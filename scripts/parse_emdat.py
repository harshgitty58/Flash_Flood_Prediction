"""Labels — parse an EM-DAT public export (https://public.emdat.be/, India 2023-2025) into Uttarakhand events.

EM-DAT records one row per disaster, usually at state level. Only rows that name Uttarakhand districts and last
<= MAX_EVENT_DAYS are expanded to district-day events (same schema as curated_dataset/flood_inventory/
supplement_2024_2025.csv). Long multi-state monsoon aggregates carry no usable district/date, so they go to a
separate "context" file (state-wide wet periods, e.g. to flag uncertain negatives) — never to labels.
Run: python scripts/parse_emdat.py [path/to/export.xlsx]   (default: newest data/external/labels/emdat/*.xlsx)
"""
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/external/labels"
MAX_EVENT_DAYS = 4
TYPES = {"Flood", "Mass movement (wet)", "Glacial lake outburst flood"}
SKIP_SUBTYPES = {"Avalanche (wet)"}
# canonical names as used by the station table / curated supplement
DISTRICTS = {"Almora": "Almora", "Bageshwar": "Bageshwar", "Chamoli": "Chamoli", "Champawat": "Champawat",
             "Dehradun": "Dehradun", "Haridwar": "Haridwar", "Nainital": "Nainital", "Pauri": "Pauri Garhwal",
             "Pithoragarh": "Pithoragarh", "Rudra ?prayag": "Rudraprayag", "Tehri": "Tehri Garhwal",
             "Udh?am Singh Nagar|US Nagar": "Udham Singh Nagar", "Uttar ?kashi": "Uttarkashi"}


def _date(r, p):
    return pd.Timestamp(int(r[f"{p} Year"]), int(r[f"{p} Month"]), int(r[f"{p} Day"])) if pd.notna(r[f"{p} Day"]) else pd.NaT


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else max(OUT.glob("emdat/*.xlsx"), key=lambda p: p.stat().st_mtime)
    d = pd.read_excel(src, sheet_name=0)
    d = d[d["Location"].astype(str).str.contains("Uttarakhand|Uttaranchal", case=False)
          | d["Admin Units"].astype(str).str.contains("Uttarakhand", case=False)]
    d = d[d["Disaster Type"].isin(TYPES) & ~d["Disaster Subtype"].isin(SKIP_SUBTYPES)]

    events, context = [], []
    for _, r in d.iterrows():
        start, end = _date(r, "Start"), _date(r, "End")
        end = start if pd.isna(end) else end
        loc = str(r["Location"])
        districts = [canon for pat, canon in DISTRICTS.items() if re.search(pat, loc, re.I)]
        days = (end - start).days + 1 if pd.notna(start) else None
        if districts and days and days <= MAX_EVENT_DAYS:
            for dist in districts:
                for k, day in enumerate(pd.date_range(start, end)):
                    events.append({"event_id": f"EMDAT-{r['DisNo.']}-{dist[:4].upper()}-{k}", "date": day.date(),
                                   "district": dist, "place": loc[:120], "type": str(r["Disaster Subtype"]).lower(),
                                   "date_confidence": "high" if days == 1 else "medium",
                                   "note": f"EM-DAT {r['Disaster Type']}; {days}-day span; deaths {r['Total Deaths']}",
                                   "source_url": f"https://public.emdat.be/ (DisNo. {r['DisNo.']})"})
        else:
            context.append({"disno": r["DisNo."], "start": start.date() if pd.notna(start) else None,
                            "end": end.date() if pd.notna(end) else None, "type": r["Disaster Subtype"],
                            "location": loc, "deaths": r["Total Deaths"],
                            "reason": "multi-state / no district" if not districts else f"{days}-day span"})

    OUT.mkdir(parents=True, exist_ok=True)
    ev = pd.DataFrame(events).sort_values(["date", "district"]) if events else pd.DataFrame()
    ev.to_csv(OUT / "emdat_uttarakhand_events.csv", index=False)
    pd.DataFrame(context).to_csv(OUT / "emdat_uttarakhand_context.csv", index=False)
    print(f"{src.name}: {len(d)} Uttarakhand flood rows -> {len(ev)} district-day events, {len(context)} context periods")
    if len(ev):
        print(ev[["date", "district", "type", "date_confidence"]].to_string(index=False))


if __name__ == "__main__":
    main()
