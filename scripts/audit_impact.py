"""Audit every scored building against the official river-setback rules, per region (see build_impact_layer.py).

  C1 consistency   each building's class == tier level in zone A (<= 50 m), -1 in B (50-100 m), -2 in C (100-200 m),
                   MINIMAL outside 200 m (NGT 2017, Jal Shakti 2025, Uttarakhand HC 2013)
  C2 zone check    zone recomputed from the stored distance matches the stored zone
  F1 dry-day alert centre at >= ALERT with < 15.6 mm rain in 24 h (IMD 'moderate' lower bound) at the gauge: an
                   ML district-prior alert, reported (not overridden: the deployed tier is kept)
  F2 no rivers     area where > 30 % of buildings are > 2 km from any mapped river/stream (OSM gap or plains with
                   canals/drains only), reported
Writes results/impact/impact_audit.csv. Run: python scripts/audit_impact.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TIERS = ["NORMAL", "WATCH", "ALERT", "SEVERE", "EXTREME"]
CLASSES = ["MINIMAL", "LOW", "MODERATE", "HIGH", "CRITICAL"]
ZONES_M = (50.0, 100.0, 200.0)


def cls(s):
    return np.select([s >= 80, s >= 60, s >= 40, s >= 20], [4, 3, 2, 1], 0)


def main():
    im = json.loads((ROOT / "web/public/data/impact.json").read_text())
    cen = pd.DataFrame(im["station_p"])
    snap = json.loads((ROOT / "web/public/data/snapshot.json").read_text())
    T = pd.Timestamp(snap["replay_time"]).tz_localize(None)
    trig = {s["station"]: s.get("trigger") for s in snap["stations"]}
    ds = pd.read_parquet(ROOT / "data/processed/final/uttarakhand_flash_flood_ml_dataset.parquet", columns=["station", "datetime", "rain_24h"])
    last = ds[(ds["datetime"] <= T) & (ds["datetime"] > T - pd.Timedelta(days=7))].sort_values("datetime").groupby("station").tail(1).set_index("station")["rain_24h"]

    b = pd.DataFrame([f["properties"] for f in json.loads((ROOT / "results/impact/buildings.geojson").read_text())["features"]])
    lv = cen["tier"].fillna("NORMAL").map(TIERS.index).to_numpy()
    zone = np.searchsorted(np.array(ZONES_M), b["d"].to_numpy(), side="left")
    z = b["z"].to_numpy()  # zone from the unrounded distance at build time
    expected = np.where(z <= 2, np.clip(lv[b["st"]] - z, 0, 4), 0)
    b["c1_ok"] = cls(b["s"].to_numpy()) == expected
    # stored d is rounded to whole metres, so allow 1 m at the 50/100/200 m boundaries
    near_edge = np.min(np.abs(b["d"].to_numpy()[:, None] - np.array(ZONES_M)[None, :]), axis=1) <= 1
    b["c2_ok"] = (zone == z) | near_edge

    rows = []
    for i, g in b.groupby("st"):
        c = cen.loc[i]
        rain = last.get(c.station)
        rows.append({"area": c.station, "src": int(c.src), "tier": c.tier, "rain_24h": None if rain is None or pd.isna(rain) else round(float(rain), 1),
                     "buildings": len(g), **{f"zone_{z}": int((g.z == k).sum()) for k, z in enumerate("ABC")},
                     **{f"{n}": int((cls(g.s.to_numpy()) == k).sum()) for k, n in list(enumerate(CLASSES))[::-1]},
                     "C1_mismatch": int((~g.c1_ok).sum()), "C2_mismatch": int((~g.c2_ok).sum()),
                     "F1_dry_alert": bool(c.src != 2 and TIERS.index(c.tier or "NORMAL") >= 2 and (rain is None or rain < 15.6) and trig.get(c.station, "ml") != "rainfall"),
                     "F2_far_%": round(100 * (g.d > 2000).mean(), 1)})
    a = pd.DataFrame(rows).sort_values(["src", "CRITICAL", "HIGH"], ascending=[True, False, False])
    a.to_csv(ROOT / "results/impact/impact_audit.csv", index=False)
    pd.set_option("display.width", 250)
    print(a.to_string(index=False))
    print(f"\nbuildings {len(b):,} | C1 class mismatches {(~b.c1_ok).sum()} | C2 zone mismatches {(~b.c2_ok).sum()}")
    print("zones (all):", {z: int((b.z == k).sum()) for k, z in enumerate(["A <=50m", "B 50-100m", "C 100-200m", "outside"])})
    print("classes (live gauges):", {n: int((cls(b[b.src == 0].s.to_numpy()) == k).sum()) for k, n in enumerate(CLASSES)})
    print("F1 dry-day ML alerts:", list(a.loc[a.F1_dry_alert, "area"]), "| F2 areas >30 % far from rivers:", list(a.loc[a["F2_far_%"] > 30, "area"]))


if __name__ == "__main__":
    main()
