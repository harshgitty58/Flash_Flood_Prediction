"""Space mode end-to-end runner: area + flood date → flood/debris map (+ later: damage, cut-off, sitrep).

Run: python -m src.space.run --name dharali --bbox 78.70,30.98,78.90,31.10 --date "2025-08-05 08:15"
     (date in UTC; bbox W,S,E,N in WGS84). Outputs: results/space/<name>/
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

from src.config import PROJECT_ROOT
from src.space import ai, data, flood, impact


def save_tif(path: Path, arr: np.ndarray, grid: data.Grid):
    with rasterio.open(path, "w", driver="GTiff", height=grid.height, width=grid.width, count=1, dtype=arr.dtype,
                       crs=grid.crs, transform=grid.transform, compress="deflate") as dst:
        dst.write(arr, 1)


def run(name: str, bbox: tuple, event: pd.Timestamp, res=10.0) -> dict:
    out = PROJECT_ROOT / "results/space" / name
    out.mkdir(parents=True, exist_ok=True)
    grid = data.make_grid(bbox, res)
    print(f"grid {grid.width}x{grid.height} @ {res} m, {grid.crs}")
    pairs = data.s1_pairs(bbox, event)
    print("S1 pairs:", [(p["orbit"], p["state"], p["before_t"][:16], p["after_t"][:16]) for p in pairs])
    pairs_db = [(data.s1_db(p["before"], grid), data.s1_db(p["after"], grid)) for p in pairs]
    z = data.dem(grid)
    osm = data.osm_before(bbox, event)
    (out / "osm_before.json").write_text(json.dumps(osm), encoding="utf-8")
    perm = flood.permanent_water(osm["water"], grid)
    corr = flood.corridor(osm["waterways"], grid)
    cls, stats = flood.detect(pairs_db, z, perm, grid, [(p["after"]["geometry"], p["state"]) for p in pairs], corr)
    save_tif(out / "flood_class.tif", cls, grid)
    save_tif(out / "dem.tif", z.astype("float32"), grid)
    summary = {"name": name, "bbox": bbox, "event_utc": str(event), "grid": {"crs": grid.crs, "res_m": res, "w": grid.width, "h": grid.height},
               "s1_pairs": [{k: p[k] for k in ("orbit", "state", "before_t", "after_t")} | {"before_id": p["before"]["id"], "after_id": p["after"]["id"]} for p in pairs],
               "osm_snapshot": osm["_snapshot"], "osm_counts": {k: len(v.get("features", [])) for k, v in osm.items() if not k.startswith("_")},
               "flood": stats, "method": flood.__doc__.strip().splitlines()[0]}
    method = "rule baseline (UN-SPIDER + ESA layover/shadow + 200 m corridor)"
    if ai.available():   # AI model is the primary detector when weights exist; rule map kept for comparison
        save_tif(out / "flood_class_rule.tif", cls, grid)
        flood_any = np.zeros(cls.shape, bool)
        for p in pairs:
            post = (data.s1_db(p["after"], grid, "vv"), data.s1_db(p["after"], grid, "vh"))
            pre1 = (data.s1_db(p["before"], grid, "vv"), data.s1_db(p["before"], grid, "vh"))
            pre2 = (data.s1_db(p["before2"], grid, "vv"), data.s1_db(p["before2"], grid, "vh"))
            flood_any |= ai.predict(post, pre1, pre2, z) == 2
        stats["ai_flood_km2_all"] = round(float(flood_any.sum() * res * res / 1e6), 3)
        flood_any &= corr & ~perm
        cls = np.where(perm, flood.PERMANENT, np.where(flood_any, flood.WATER, flood.NONE)).astype("uint8")
        stats["ai_flood_km2_corridor"] = round(float(flood_any.sum() * res * res / 1e6), 3)
        method = "AI U-Net (Kuro Siwo) within the 200 m river corridor"
        save_tif(out / "flood_class.tif", cls, grid)
        summary["flood"] = stats
    summary["detector"] = method
    dmg = impact.damage(osm, cls, grid)
    cut = impact.cut_off(osm, dmg, bbox)
    for layer in ("buildings", "roads", "bridges"):
        (out / f"{layer}_hit.geojson").write_text(json.dumps(dmg[layer]), encoding="utf-8")
    (out / "cutoff.json").write_text(json.dumps(cut, indent=2), encoding="utf-8")
    summary |= {"damage": dmg["counts"], "cutoff": {k: cut.get(k) for k in ("destination", "counts", "removed_road_ids")}}
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"flood": summary["flood"], "damage": summary["damage"], "cutoff": summary["cutoff"]}, indent=1))
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--bbox", required=True, help="W,S,E,N")
    ap.add_argument("--date", required=True, help="event time UTC, e.g. '2025-08-05 08:15'")
    ap.add_argument("--res", type=float, default=10.0)
    a = ap.parse_args()
    run(a.name, tuple(float(v) for v in a.bbox.split(",")), pd.Timestamp(a.date), a.res)
