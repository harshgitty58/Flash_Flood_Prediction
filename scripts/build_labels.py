"""Labels — build one auditable Uttarakhand flood-event list for 2022-2025 (LABELS_PLAN.md §2-4).

Sources (data/external/labels/ unless noted):
  imd      data/processed/cleaned/flood_inventory_cleaned.parquet   official inventory (training labels v1)
  sandrp   sandrp/uttarakhand_cloudbursts_{2022,2023}.html         "DD Month; District: description" entries
  sphere   sitreps_manual.csv                                      hand-checked rows from Sphere India SitReps
  emdat    emdat_uttarakhand_events.csv                            from scripts/parse_emdat.py
  curated  curated_dataset/flood_inventory/supplement_2024_2025.csv news list with one URL per event

Outputs: labels_2022_2025.csv (merged events), labels_daily.csv (one row per source per district-day, used by the
audit and label v2), excluded.csv, unresolved.csv, labels_summary.json.
Run: python scripts/build_labels.py
"""
import difflib
import html
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.config import CLEANED_DIR, OFFICIAL_UTTARAKHAND_DISTRICTS  # noqa: E402
from src.district_mapping import standardize_district_name  # noqa: E402

LAB = ROOT / "data/external/labels"
START = pd.Timestamp("2022-01-01")
CANON = set(OFFICIAL_UTTARAKHAND_DISTRICTS)
CONF_RANK = {"low": 0, "medium": 1, "high": 2}
SEV_RANK = {"low": 0, "moderate": 1, "high": 2}
ALIASES = {"tehri": "Tehri Garhwal", "pauri": "Pauri Garhwal", "garhwal": "Pauri Garhwal", "us nagar": "Udham Singh Nagar",
           "udam singh nagar": "Udham Singh Nagar", "rudra prayag": "Rudraprayag", "uttar kashi": "Uttarkashi"}
# places reported without a district
PLACES = {"joshimath": "Chamoli", "tharali": "Chamoli", "dewal": "Chamoli", "gairsain": "Chamoli", "nanda nagar": "Chamoli",
          "kapkot": "Bageshwar", "dharchula": "Pithoragarh", "munsiyari": "Pithoragarh", "ghansali": "Tehri Garhwal",
          "kedarnath": "Rudraprayag", "ukhimath": "Rudraprayag", "raipur": "Dehradun", "sahastradhara": "Dehradun",
          "maldevta": "Dehradun", "rishikesh": "Dehradun", "roorkee": "Haridwar", "haldwani": "Nainital", "kotdwar": "Pauri Garhwal", "srinagar": "Pauri Garhwal", "mussoorie": "Dehradun", "haldwani": "Nainital", "kathgodam": "Nainital", "kotdwar": "Pauri Garhwal",
          "yamkeshwar": "Pauri Garhwal", "thalisain": "Pauri Garhwal", "dharali": "Uttarkashi", "harsil": "Uttarkashi"}
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
COLS = ["date", "end_date", "district", "place", "type", "hour_local", "deaths", "missing", "severity", "date_confidence",
        "source", "source_ref", "evidence"]


def resolve(name: str) -> str | None:
    """Raw district/place string -> canonical district, or None."""
    s = re.sub(r"[^a-z ]", " ", str(name).lower()).strip()
    s = re.sub(r"\s+", " ", s)
    if not s:
        return None
    std = standardize_district_name(s)
    if std in CANON:
        return std
    if s in ALIASES:
        return ALIASES[s]
    for k, v in PLACES.items():
        if k in s:
            return v
    keys = [d.lower() for d in CANON] + list(ALIASES)
    hit = difflib.get_close_matches(s, keys, n=1, cutoff=0.8)  # typos such as "Pithoragrah"
    if hit:
        return ALIASES.get(hit[0]) or next(d for d in CANON if d.lower() == hit[0])
    return None


# ------------------------------------------------------------------ classification of free text
def classify(text: str) -> str:
    t = text.lower()
    for pat, typ in ((r"cloud ?burst", "cloudburst"), (r"flash ?flood", "flash_flood"), (r"urban flood|water ?logging", "urban_flood"),
                     (r"muck|debris", "debris_flow"), (r"landslide", "landslide_rain"), (r"flood", "riverine_flood")):
        if re.search(pat, t):
            return typ
    return "heavy_rain_damage"


def severity(text: str) -> str:
    t = text.lower()
    if re.search(r"\b(died|killed|killing|dead|deaths?|buried|missing|lost (?:their|his|her) li)", t):
        return "high"
    if re.search(r"\b(house|home|bridge|road|shop|hotel|school|building)s?\b", t):
        return "moderate"
    return "low"


def excluded_reason(text: str) -> str | None:
    t = text.lower()
    if re.search(r"lightn|lighten", t) and not re.search(r"flood|cloud ?burst|debris|muck|landslide|washed", t):
        return "lightning only"
    if re.search(r"avalanche|snow|hail", t) and not re.search(r"flood|cloud ?burst|debris|muck", t):
        return "snow/avalanche/hail"
    return None


# ------------------------------------------------------------------ sources
def html_text(path: Path) -> str:
    s = path.read_text(encoding="utf-8", errors="ignore")
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    m = re.search(r'(?is)<div class="entry-content[^"]*">(.*?)<footer', s)
    s = m.group(1) if m else s
    s = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h\d>|</tr>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"[ \t\xa0]+", " ", html.unescape(s))


HDR = re.compile(r"^\s*(\d{1,2})\s*(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*[;,]?\s*(.*)$", re.I)
SUB = re.compile(r"^\s*([A-Z][A-Za-z ]{2,25}?)\s*:\s*(.+)$")
STOP = re.compile(r"summary table|high rainfall days|^\s*summary\s*:", re.I)


def parse_sandrp(path: Path, year: int, excluded: list, unresolved: list) -> list[dict]:
    """Narrative entries 'DD Month; District: text'; a header without a district opens a block whose
    'District : text' sub-paragraphs share its date (e.g. 20 Aug 2022, multiple cloudbursts)."""
    entries, cur = [], None
    for ln in html_text(path).splitlines():
        if STOP.search(ln):
            break
        m = HDR.match(ln)
        if m:
            day, mon, rest = int(m.group(1)), MONTHS[m.group(2).lower()[:3]], m.group(3)
            head = rest.split(":")[0] if ":" in rest[:40] else " ".join(rest.split()[:3])
            dist = resolve(head) or resolve(" ".join(rest.split()[:1]))
            cur = {"date": pd.Timestamp(year, mon, day), "district": dist, "text": rest, "head": rest, "block": dist is None}
            entries.append(cur)
        elif cur is not None:
            s = SUB.match(ln)
            if cur["block"] and s and resolve(s.group(1)):
                cur = {"date": cur["date"], "district": resolve(s.group(1)), "text": s.group(2), "head": s.group(2), "block": True}
                entries.append(cur)
            else:
                cur["text"] += " " + ln.strip()
    rows = []
    for e in entries:
        text = re.sub(r"\[[ivxlc]+\]", "", e["text"]).strip()
        ref = f"sandrp/{path.name}"
        if e["district"] is None:
            if not re.match(r"multiple|several", text, re.I):
                unresolved.append({"source": "sandrp", "date": e["date"].date(), "text": text[:200], "source_ref": ref})
            continue
        why = excluded_reason(re.split(r"(?<=\.)\s", e["head"])[0])  # judge by the lead sentence, not later context
        if why:
            excluded.append({"source": "sandrp", "date": e["date"].date(), "district": e["district"], "reason": why,
                             "text": text[:200], "source_ref": ref})
            continue
        rows.append({"date": e["date"], "end_date": e["date"], "district": e["district"], "place": "", "type": classify(text),
                     "severity": severity(text), "date_confidence": "high", "source": "sandrp", "source_ref": ref,
                     "evidence": text[:240]})
    return rows


def load_imd() -> list[dict]:
    inv = pd.read_parquet(CLEANED_DIR / "flood_inventory_cleaned.parquet")
    inv["district"] = inv["district"].map(lambda d: resolve(d) or d)
    inv = inv[inv["district"].isin(CANON) & (inv["start_datetime"] >= START)]
    rows = []
    for _, r in inv.drop_duplicates(["district", "start_datetime"]).iterrows():
        cause = str(r["main_cause"])
        rows.append({"date": r["start_datetime"].normalize(), "end_date": (r["end_datetime"] if pd.notna(r["end_datetime"]) else r["start_datetime"]).normalize(),
                     "district": r["district"], "type": classify(cause) if classify(cause) != "heavy_rain_damage" else "heavy_rain_flood",
                     "deaths": r["fatalities"], "severity": "high" if (r["fatalities"] or 0) > 0 else "moderate",
                     "date_confidence": "high", "source": "imd", "source_ref": r["uei"], "evidence": cause})
    return rows


def load_csv_source(path: Path, source: str) -> list[dict]:
    if not path.exists():
        return []
    d = pd.read_csv(path, parse_dates=["date"])
    out = []
    for _, r in d.iterrows():
        row = {c: r[c] for c in COLS if c in d.columns and pd.notna(r[c])}
        row.setdefault("end_date", r["date"])
        row["end_date"] = pd.Timestamp(row["end_date"])
        row["district"] = resolve(r["district"]) or r["district"]
        row["source"] = row.get("source", source)
        if source == "curated":
            row.update(type=str(r["type"]).split("/")[0].strip().replace(" ", "_"), source_ref=r["source_url"], evidence=r.get("note", ""),
                       severity=severity(str(r.get("note", ""))))
        if source == "emdat":
            row["source_ref"] = r["source_url"]
        out.append(row)
    if source == "emdat":  # one row per day per district in the parsed file -> collapse to the event span
        e = pd.DataFrame(out)
        e["disno"] = e["source_ref"].str.extract(r"DisNo\. ([\w-]+)")[0]
        out = [{**g.iloc[0].to_dict(), "date": g["date"].min(), "end_date": g["date"].max()} for _, g in e.groupby(["disno", "district"])]
        for o in out:
            o.pop("disno", None)
    return out


# ------------------------------------------------------------------ merge
def family(src: str) -> set:
    return {s.strip() for s in str(src).split(";") if s.strip()}


def merge(rows: pd.DataFrame) -> pd.DataFrame:
    """Same district, spans within 1 day of each other -> one event. Corroboration by >= 2 independent
    source families raises date confidence one step (low->medium, medium->high)."""
    out = []
    for dist, g in rows.sort_values("date").groupby("district"):
        clusters, cur, cur_end = [], [], None
        for _, r in g.iterrows():
            if cur and r["date"] > cur_end + pd.Timedelta(days=1):
                clusters.append(cur); cur = []
            cur.append(r)
            cur_end = max(cur_end, r["end_date"]) if len(cur) > 1 else r["end_date"]
        clusters.append(cur)
        for c in clusters:
            c = pd.DataFrame(c)
            best = c.loc[c["date_confidence"].map(CONF_RANK).sort_values(ascending=False, kind="stable").index[0]]
            fams = set().union(*[family(s) for s in c["source"]])
            conf = max(c["date_confidence"], key=CONF_RANK.get)
            if len(fams) >= 2 and conf != "high":
                conf = {"low": "medium", "medium": "high"}[conf]
            places = "; ".join(dict.fromkeys(p for p in c.get("place", pd.Series(dtype=str)).fillna("") if p))
            out.append({"date": c["date"].min().date(), "end_date": c["end_date"].max().date(), "district": dist,
                        "place": places[:160], "type": best.get("type"), "hour_local": c.get("hour_local", pd.Series(dtype=object)).dropna().iloc[0] if c.get("hour_local") is not None and c["hour_local"].notna().any() else None,
                        "deaths": pd.to_numeric(c.get("deaths"), errors="coerce").max() if "deaths" in c else None,
                        "severity": max(c["severity"].fillna("low"), key=SEV_RANK.get), "date_confidence": conf,
                        "sources": ";".join(sorted(fams)), "source_count": len(fams), "n_reports": len(c),
                        "source_ref": " | ".join(dict.fromkeys(str(s) for s in c["source_ref"]))[:400]})
    ev = pd.DataFrame(out).sort_values(["date", "district"]).reset_index(drop=True)
    ev.insert(0, "event_id", [f"EV-{d:%Y%m%d}-{x[:4].upper()}" for d, x in zip(pd.to_datetime(ev["date"]), ev["district"])])
    return ev


def daily(rows: pd.DataFrame) -> pd.DataFrame:
    """One row per (source family, district, day) — the unit for the audit and label v2."""
    recs = []
    for _, r in rows.iterrows():
        for f in family(r["source"]):
            for d in pd.date_range(r["date"], r["end_date"]):
                recs.append({"date": d.date(), "district": r["district"], "source": f, "date_confidence": r["date_confidence"],
                             "severity": r.get("severity"), "type": r.get("type")})
    d = pd.DataFrame(recs)
    d["_c"] = d["date_confidence"].map(CONF_RANK)
    return d.sort_values("_c", ascending=False).drop_duplicates(["source", "district", "date"]).drop(columns="_c").sort_values(["date", "district", "source"])


def main():
    excluded, unresolved = [], []
    rows = load_imd()
    for year in (2022, 2023):
        p = LAB / f"sandrp/uttarakhand_cloudbursts_{year}.html"
        if p.exists():
            rows += parse_sandrp(p, year, excluded, unresolved)
    rows += load_csv_source(LAB / "sitreps_manual.csv", "sphere")
    rows += load_csv_source(LAB / "emdat_uttarakhand_events.csv", "emdat")
    rows += load_csv_source(ROOT / "curated_dataset/flood_inventory/supplement_2024_2025.csv", "curated")

    raw = pd.DataFrame(rows)
    raw["date"], raw["end_date"] = pd.to_datetime(raw["date"]), pd.to_datetime(raw["end_date"])
    bad = ~raw["district"].isin(CANON)
    for _, r in raw[bad].iterrows():
        unresolved.append({"source": r["source"], "date": r["date"].date(), "text": f"district={r['district']}", "source_ref": r["source_ref"]})
    raw = raw[~bad]
    raw = raw[(raw["end_date"] - raw["date"]).dt.days <= 3]  # >4-day spans are context, not events (plan §3)

    events, days = merge(raw), daily(raw)
    events.to_csv(LAB / "labels_2022_2025.csv", index=False)
    days.to_csv(LAB / "labels_daily.csv", index=False)
    pd.DataFrame(excluded).to_csv(LAB / "excluded.csv", index=False)
    pd.DataFrame(unresolved, columns=["source", "date", "text", "source_ref"]).to_csv(LAB / "unresolved.csv", index=False)
    yr = pd.to_datetime(events["date"]).dt.year
    summary = {"events": len(events), "district_days": int(days[["district", "date"]].drop_duplicates().shape[0]),
               "by_year": yr.value_counts().sort_index().to_dict(),
               "by_confidence": events["date_confidence"].value_counts().to_dict(),
               "by_source_family": days.groupby("source")[["district", "date"]].apply(lambda g: len(g.drop_duplicates())).to_dict(),
               "corroborated_events": int((events["source_count"] >= 2).sum()),
               "excluded": len(excluded), "unresolved": len(unresolved)}
    (LAB / "labels_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
