"""
Latency: cut the single 8.7 MB buildings.geojson into z12 slippy-map tiles + a light overview (level of detail).

  web/public/data/bld/12/{x}/{y}.json   buildings whose centroid falls in that tile (loaded only when in view)
  web/public/data/bld/index.json        tile list with counts per impact class and the tile centre (overview layer
                                        drawn below zoom 12, and lets the client know which tiles exist)
The backend serves the same files; the static build works without it.
Run: python scripts/build_building_tiles.py
"""
import json
import math
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web/public/data"
Z = 12
MAX_PER_TILE, MAX_Z = 3000, 15  # adaptive quadtree: split dense tiles until <= MAX_PER_TILE buildings
CLASSES = [(80, "CRITICAL"), (60, "HIGH"), (40, "MODERATE"), (20, "LOW"), (0, "MINIMAL")]


def tile_of(lon: float, lat: float, z: int = Z) -> tuple[int, int]:
    n = 2 ** z
    x = int((lon + 180) / 360 * n)
    y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
    return x, y


def tile_center(x: int, y: int, z: int = Z) -> tuple[float, float]:
    n = 2 ** z
    lon = (x + 0.5) / n * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 0.5) / n))))
    return lon, lat


def main():
    SRC = ROOT / "results/impact/buildings.geojson"  # full layer stays out of the web bundle; only tiles ship
    src = json.loads(SRC.read_text())
    pts = []
    for f in src["features"]:
        ring = f["geometry"]["coordinates"][0]
        pts.append((sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring), f))

    def split(z, x, y, items):
        if len(items) <= MAX_PER_TILE or z == MAX_Z:
            yield z, x, y, items
            return
        kids = defaultdict(list)
        for it in items:
            kids[tile_of(it[0], it[1], z + 1)].append(it)
        for (cx, cy), sub in kids.items():
            yield from split(z + 1, cx, cy, sub)

    top = defaultdict(list)
    for it in pts:
        top[tile_of(it[0], it[1])].append(it)
    out = DATA / "bld"
    shutil.rmtree(out, ignore_errors=True)
    index = []
    for (x0, y0), items in top.items():
        for z, x, y, sub in split(Z, x0, y0, items):
            feats = [it[2] for it in sub]
            p = out / str(z) / str(x) / f"{y}.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, separators=(",", ":")))
            counts = defaultdict(int)
            for f in feats:
                counts[next(n for c, n in CLASSES if f["properties"]["s"] >= c)] += 1
            n2 = 2 ** z
            w, e = x / n2 * 360 - 180, (x + 1) / n2 * 360 - 180
            nlat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n2))))
            slat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n2))))
            lon, lat = tile_center(x, y, z)
            index.append({"z": z, "x": x, "y": y, "bbox": [round(w, 5), round(slat, 5), round(e, 5), round(nlat, 5)],
                          "lon": round(lon, 5), "lat": round(lat, 5), "n": len(feats),
                          "max_s": max(f["properties"]["s"] for f in feats), "by_class": dict(counts), "bytes": p.stat().st_size})
    (out / "index.json").write_text(json.dumps({"z": Z, "tiles": index}, separators=(",", ":")))
    sizes = sorted(t["bytes"] for t in index)
    print(f"{len(src['features']):,} buildings -> {len(index)} tiles; median tile {sizes[len(sizes)//2]/1e3:.0f} KB, "
          f"max {sizes[-1]/1e3:.0f} KB (was one {SRC.stat().st_size/1e6:.1f} MB file)")


if __name__ == "__main__":
    main()
