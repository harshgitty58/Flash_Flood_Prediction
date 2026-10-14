"""Export Space-mode results (results/space/<name>/) for the web app → web/public/data/space.json (+ map image).

The backend serves it at /data/space like every other exported JSON. Flood/permanent-water pixels are vectorised
(simplified 10 m) and reprojected to WGS84; only hit buildings are exported (all roads/bridges keep their hit flag).
Run: python scripts/export_space.py --name dharali
"""
import argparse
import json
import shutil
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import shapes
from rasterio.warp import transform_geom
from shapely.geometry import mapping, shape

ROOT = Path(__file__).resolve().parents[1]


def polygons(tif: Path, classes: dict) -> dict:
    with rasterio.open(tif) as src:
        a, T, crs = src.read(1), src.transform, src.crs
    feats = []
    for cls, name in classes.items():
        m = (a == cls).astype("uint8")
        for g, v in shapes(m, mask=m.astype(bool), transform=T):
            geom = shape(g).simplify(10, preserve_topology=True)
            if geom.is_empty or geom.area < 400:  # drop specks < 400 m²
                continue
            feats.append({"type": "Feature", "geometry": transform_geom(crs, "EPSG:4326", mapping(geom), precision=5),
                          "properties": {"class": name, "area_m2": round(geom.area)}})
    return {"type": "FeatureCollection", "features": feats}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--name", default="dharali"); n = ap.parse_args().name
    d = ROOT / "results/space" / n
    s = json.loads((d / "summary.json").read_text())
    meta_p = ROOT / "models/space/floodseg_meta.json"
    meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
    load = lambda f: json.loads((d / f).read_text())  # noqa: E731
    b = load("buildings_hit.geojson"); b["features"] = [f for f in b["features"] if f["properties"]["hit"]]
    out = {"name": n, "event_utc": s["event_utc"], "bbox": s["bbox"], "detector": s.get("detector"), "osm_snapshot": s["osm_snapshot"],
           "s1_pairs": s["s1_pairs"], "flood": s["flood"], "damage": s["damage"], "cutoff": load("cutoff.json"),
           "model": {k: meta.get(k) for k in ("arch", "flood_threshold", "water_threshold", "test_scores_unseen_events", "training_data", "trained_utc")},
           "layers": {"flood": polygons(d / "flood_class.tif", {1: "flood", 3: "permanent water"}), "buildings_hit": b,
                      "roads": load("roads_hit.geojson"), "bridges": load("bridges_hit.geojson")},
           "debris": ({"summary": s["debris_rule"], "cutoff": load("cutoff_debris.json"),
                       "polygons": polygons(d / "debris_class.tif", {2: "possible debris"}),
                       "buildings_hit": {"type": "FeatureCollection", "features": [f for f in load("buildings_debris.geojson")["features"] if f["properties"]["hit"]]},
                       "roads": {"type": "FeatureCollection", "features": [f for f in load("roads_debris.geojson")["features"] if f["properties"]["hit"]]}}
                      if (d / "debris_class.tif").exists() else None),
           "sitrep": (d / "sitrep.md").read_text(encoding="utf-8") if (d / "sitrep.md").exists() else ""}
    web = ROOT / "web/public/data"
    (web / "space.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    img = ROOT / "web/public/img/space"; img.mkdir(parents=True, exist_ok=True)
    if (d / "map.png").exists():
        shutil.copy(d / "map.png", img / f"{n}.png")
    print(f"space.json: {len(out['layers']['flood']['features'])} flood polygons, {len(b['features'])} hit buildings, "
          f"{(web / 'space.json').stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
