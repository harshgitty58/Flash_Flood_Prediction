"""Home-page imagery: Sentinel-2 L2A true-colour scenes of Uttarakhand flood sites (no people — Track B rule).

Searches the public Earth Search STAC (Element 84, AWS open data, no account) for the clearest scene in a window,
reads only the needed window of the 10 m 'visual' COG, and writes a compressed WebP to web/public/img/home/.
Attribution: "Contains modified Copernicus Sentinel data <year>" (credits.json, shown in the page footer).
Run: python scripts/fetch_home_imagery.py
"""
import io
import json
from pathlib import Path

import numpy as np
import rasterio
import requests
from PIL import Image, ImageEnhance
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web/public/img/home"
STAC = "https://earth-search.aws.element84.com/v1/search"
# name, centre (lat, lon), half-size (km, km), date window, caption
SITES = [
    ("hero-alaknanda", (30.42, 79.42), (14, 8), "2024-10-01/2025-01-31", "Alaknanda valley, Chamoli: the Garhwal Himalaya from Sentinel-2"),
    ("dharali", (31.03, 78.80), (8, 4.5), "2025-09-20/2025-12-15", "Dharali and the Kheer Ganga debris fan after the 5 Aug 2025 flash flood"),
    ("kedarnath", (30.68, 79.03), (8, 4.5), "2024-10-01/2024-12-31", "Mandakini valley, Kedarnath route (31 Jul 2024 cloudburst)"),
    ("haridwar", (29.96, 78.17), (8, 4.5), "2024-10-15/2025-01-31", "The braided Ganga at Haridwar, a flood-plain zoning hotspot"),
    ("haldwani", (29.22, 79.52), (8, 4.5),
     "2024-10-15/2025-01-31", "Gaula river fan at Haldwani (140 mm in 24 h on 12 Sep 2024)"),
    ("joshimath", (30.56, 79.56), (8, 4.5), "2024-10-01/2024-12-31", "Joshimath and the Alaknanda–Dhauliganga confluence"),
]


def km_box(lat, lon, hx, hy):
    k = np.cos(np.radians(lat))
    return lon - hx / (111.32 * k), lat - hy / 110.54, lon + hx / (111.32 * k), lat + hy / 110.54


def best_item(bbox, dates):
    q = {"collections": ["sentinel-2-l2a"], "bbox": list(bbox), "datetime": f"{dates.split('/')[0]}T00:00:00Z/{dates.split('/')[1]}T23:59:59Z",
         "query": {"eo:cloud_cover": {"lt": 15}}, "limit": 50}
    feats = requests.post(STAC, json=q, timeout=120).json().get("features", [])
    feats = [f for f in feats if "visual" in f["assets"]]
    return min(feats, key=lambda f: f["properties"]["eo:cloud_cover"]) if feats else None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    credits = []
    for name, (lat, lon), (hx, hy), dates, caption in SITES:
        bbox = km_box(lat, lon, hx, hy)
        it = best_item(bbox, dates)
        if not it:
            print("no clear scene for", name); continue
        with rasterio.open(it["assets"]["visual"]["href"]) as src:
            win = from_bounds(*transform_bounds("EPSG:4326", src.crs, *bbox), transform=src.transform)
            arr = src.read([1, 2, 3], window=win, boundless=True, fill_value=0)
        img = Image.fromarray(np.moveaxis(arr, 0, -1))
        img = ImageEnhance.Contrast(ImageEnhance.Brightness(img).enhance(1.15)).enhance(1.1)
        w = 2000 if name.startswith("hero") else 1600
        if img.width > w:
            img = img.resize((w, round(img.height * w / img.width)), Image.LANCZOS)
        buf = io.BytesIO()
        for q in (78, 70, 62, 55):
            buf = io.BytesIO(); img.save(buf, "WEBP", quality=q, method=6)
            if buf.tell() <= (380_000 if name.startswith('hero') else 300_000):
                break
        (OUT / f"{name}.webp").write_bytes(buf.getvalue())
        d = it["properties"]["datetime"][:10]
        credits.append({"file": f"{name}.webp", "caption": caption, "scene": it["id"], "date": d, "cloud": it["properties"]["eo:cloud_cover"],
                        "credit": f"Contains modified Copernicus Sentinel data {d[:4]}"})
        print(f"{name}: {it['id']} {d} cloud {it['properties']['eo:cloud_cover']:.1f}% → {img.width}x{img.height}, {buf.tell() // 1024} KB")
    (OUT / "credits.json").write_text(json.dumps(credits, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
