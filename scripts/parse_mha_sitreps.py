"""Labels — parse MHA daily flood situation reports (scripts/fetch_mha_sitreps.py) into Uttarakhand tables.

Per report (one per day, situation at 18:00 IST):
  * cumulative loss table (Annexure-I, season from 1 April): districts affected, deaths by cause (flood/drowning,
    lightning, landslide, others, total), missing, injured, houses fully / partially damaged
  * last-24 h damage row: deaths with cause text, houses damaged
  * IMD "significant rainfall recorded during last 24 hrs": rainfall range (cm) and the Uttarakhand districts
State-level damage only — the reports carry no district-level incidents, so these are NOT district flood labels.
Daily increments (deaths_new etc.) are differences of the cumulative table between consecutive reports.
Output: data/external/labels/mha_uttarakhand_daily.csv. Run: python scripts/parse_mha_sitreps.py
"""
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_labels import resolve  # noqa: E402

SRC = ROOT / "data/external/labels/mha_sitreps"
CUM_COLS = ["districts_affected", "deaths_flood", "deaths_lightning", "deaths_landslide", "deaths_other", "deaths_total",
            "missing", "injured", "houses_full", "houses_partial"]
NUM = r"(?:[\d,]+|-)"


def num(x):
    return None if x in (None, "-") else int(x.replace(",", ""))


def parse(text: str) -> dict:
    flat = re.sub(r"[ \t]+", " ", text)
    out = {}
    m = re.search(rf"\n\s*\d+\.?\s*Uttarakhand\s+((?:{NUM}\s+){{9,}}{NUM})", flat)  # cumulative row (>= 10 numbers)
    if m:
        vals = m.group(1).split()
        out.update({c: num(v) for c, v in zip(CUM_COLS, vals)})
    m = re.search(r"\n\s*\d+\.?\s*Uttarakhand\s+(-|\d+)\s+(-|\d+)\s+(-|[\d,]+)\s+(-|\d+)\s*\(([^)]*)\)", flat)  # last-24 h row
    if m:
        out["deaths_24h"], out["cause_24h"] = num(m.group(4)), re.sub(r"\s+", "", m.group(5)).lower()
    m = re.search(r"\n\s*\d+\.?\s*Uttarakhand\s+(\d{1,2}(?:\s*-\s*\d{1,2})?)\s+(\d{1,2})\s*\(([^)]*)\)", flat)  # IMD rainfall
    if m:
        lo_hi = [int(v) for v in re.findall(r"\d+", m.group(1))]
        names = re.sub(r"\s+", " ", m.group(3).replace("\n", " "))
        dists = sorted({d for part in re.split(r",|\band\b", names) if (d := resolve(re.sub(r"(\w) (\w{2,})$", r"\1\2", part.strip())))})
        out.update({"rain_cm_min": lo_hi[0], "rain_cm_max": lo_hi[-1], "rain_n_districts": int(m.group(2)),
                    "heavy_rain_districts": ";".join(dists), "heavy_rain_raw": names[:200]})
    return out


def main():
    rows = []
    for t in sorted(SRC.glob("*.txt")):
        day, uid = t.stem.split("_", 1)
        rows.append({"date": day, "uid": uid, **parse(t.read_text(encoding="utf-8"))})
    d = pd.DataFrame(rows).sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)
    d["date"] = pd.to_datetime(d["date"])
    for c in ("deaths_total", "missing", "injured", "houses_full", "houses_partial"):
        if c in d:
            prev = d[c].shift()
            new = d[c] - prev
            # the cumulative table restarts each season (1 April): a drop in April is a reset (take the value itself);
            # a drop at any other time is a reporting glitch (left empty)
            reset = (new < 0) & (d["date"].dt.month == 4)
            d[f"{c}_new"] = new.where(new >= 0, d[c].where(reset)).where(d[c].notna() & prev.notna())
    out = ROOT / "data/external/labels/mha_uttarakhand_daily.csv"
    d.to_csv(out, index=False)
    print(f"{len(d)} reports {d['date'].min():%Y-%m-%d} → {d['date'].max():%Y-%m-%d}; "
          f"cumulative rows {d['deaths_total'].notna().sum() if 'deaths_total' in d else 0}, heavy-rain rows {d['heavy_rain_districts'].notna().sum() if 'heavy_rain_districts' in d else 0}")
    cols = [c for c in ("date", "deaths_total", "deaths_total_new", "deaths_24h", "cause_24h", "houses_full_new", "heavy_rain_districts", "rain_cm_max") if c in d]
    print(d.loc[d.get("deaths_total_new", pd.Series(dtype=float)).fillna(0) > 0, cols].head(15).to_string(index=False))


if __name__ == "__main__":
    main()
