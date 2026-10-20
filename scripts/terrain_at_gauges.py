"""Terrain parameters at every gauge from the Copernicus GLO-30 DEM (PRAHAR_MASTER_PLAN.md WS-01.9 / WS-04.7).

For each gauge (web/public/data/stations.json) a 0.2 deg window (~22 km, 720 x 720 cells of 1 arc-second) is read straight
from the public cloud-optimised GeoTIFFs on AWS (s3://copernicus-dem-30m, no account), cached in data/external/glo30/,
and run through src/terrain.py: elevation, slope, aspect, TRI, TWI, SPI, flow accumulation, channels (>= 1 km2) and HAND.

Output: results/v3/terrain_at_gauges.csv (+ .md summary with a check against the Terrarium elevations used so far).
Note: upstream area is limited to the window, so for big rivers (e.g. the Ganga at Haridwar) `upstream_km2` is a
local value; `upstream_truncated` flags it. True basin areas come with HydroSHEDS (WS-01.9).
Run: python scripts/terrain_at_gauges.py
Attribution: Copernicus WorldDEM-30 (c) DLR e.V. 2010-2014 and (c) Airbus Defence and Space GmbH 2014-2018, provided under
COPERNICUS by the European Union and ESA; all rights reserved.
"""
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.merge import merge
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import terrain as T  # noqa: E402

CACHE = ROOT / "data/external/glo30"
OUT = ROOT / "results/v3"
HALF = 0.1           # degrees either side of the gauge
STEP = 1 / 3600      # GLO-30 grid (1 arc-second below 50 deg latitude)
URL = ("/vsicurl/https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_{ns}{lat:02d}_00_{ew}{lon:03d}_00_DEM/"
       "Copernicus_DSM_COG_10_{ns}{lat:02d}_00_{ew}{lon:03d}_00_DEM.tif")
ENV = {"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR", "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif", "GDAL_HTTP_MAX_RETRY": "4",
       "GDAL_HTTP_RETRY_DELAY": "2"}


def window(lat: float, lon: float) -> np.ndarray:
    f = CACHE / f"{lat:.4f}_{lon:.4f}.npy"
    if f.exists():
        return np.load(f)
    b = (lon - HALF, lat - HALF, lon + HALF, lat + HALF)
    tiles = {(la, lo) for la in range(math.floor(b[1]), math.floor(b[3]) + 1) for lo in range(math.floor(b[0]), math.floor(b[2]) + 1)}
    with rasterio.Env(**ENV):
        srcs = [rasterio.open(URL.format(ns="N", lat=la, ew="E", lon=lo)) for la, lo in sorted(tiles)]
        z, _ = merge(srcs, bounds=b, res=STEP, nodata=np.nan, dtype="float32")
        for s in srcs:
            s.close()
    z = z[0]
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(f, z)
    return z


def at_gauge(lat: float, lon: float) -> dict:
    z = window(lat, lon).astype("float64")
    z = np.where(np.isfinite(z), z, np.nanmin(z))
    dx, dy = T.metres_per_cell(lat, STEP)
    s = T.terrain_suite(z, dx, dy, channel_km2=1.0)
    r, c = z.shape[0] // 2, z.shape[1] // 2
    yy, xx = np.ogrid[:z.shape[0], :z.shape[1]]
    disk = ((yy - r) * dy) ** 2 + ((xx - c) * dx) ** 2 <= 1000 ** 2          # 1 km radius
    dist = ndimage.distance_transform_edt(~s["channel"], sampling=(dy, dx))
    # does the gauge's own contributing area reach the window border? (walk the D8 graph upstream from the gauge cell)
    down = T._downstream(s["flow_dir"])
    upstream = np.zeros(z.size, bool)
    frontier = np.array([r * z.shape[1] + c])
    while frontier.size:
        frontier = np.nonzero(np.isin(down, frontier))[0]
        upstream[frontier] = True
    up = upstream.reshape(z.shape)
    edge_hit = bool(up[[0, -1], :].any() or up[:, [0, -1]].any())
    return {"elev_m": round(z[r, c], 1), "slope_deg": round(s["slope_deg"][r, c], 2), "aspect_deg": round(float(np.nan_to_num(s["aspect_deg"][r, c], nan=-1)), 1),
            "tri_m": round(s["tri_m"][r, c], 2), "twi": round(s["twi"][r, c], 3), "spi": round(s["spi"][r, c], 3),
            "upstream_km2": round(s["upstream_km2"][r, c], 3), "hand_m": round(float(s["hand_m"][r, c]), 2),
            "dist_channel_m": round(float(dist[r, c]), 1), "relief_1km_m": round(float(z[disk].max() - z[disk].min()), 1),
            "slope_mean_1km_deg": round(float(s["slope_deg"][disk].mean()), 2), "twi_mean_1km": round(float(s["twi"][disk].mean()), 3),
            "channel_density_1km": round(float(s["channel"][disk].mean()), 4), "upstream_truncated": bool(edge_hit)}


def main():
    st = pd.DataFrame(json.loads((ROOT / "web/public/data/stations.json").read_text(encoding="utf-8")))
    rows = []
    for i, x in st.iterrows():
        t0 = time.time()
        try:
            rows.append({"station": x.station, "district": x.district, "kind": x.kind, "lat": x.lat, "lon": x.lon, **at_gauge(x.lat, x.lon)})
            print(f"{i + 1:2d}/{len(st)} {x.station:28s} {time.time() - t0:5.1f} s", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"{i + 1:2d}/{len(st)} {x.station:28s} FAILED {type(e).__name__}: {e}", flush=True)
    df = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "terrain_at_gauges.csv", index=False)

    # check against the Terrarium (zoom 12) terrain the project used so far (src/enrich_features.py)
    old = pd.read_parquet(ROOT / "data/processed/final/uttarakhand_flash_flood_ml_dataset.parquet", columns=["station", "terrain_elev_m", "terrain_slope_deg"]) \
        .dropna().drop_duplicates("station") if "terrain_elev_m" in pd.read_parquet(ROOT / "data/processed/final/uttarakhand_flash_flood_ml_dataset.parquet").columns else None
    lines = ["# Terrain at gauges: Copernicus GLO-30 (30 m)", "",
             f"{len(df)} of {len(st)} gauges processed with `src/terrain.py` (0.2° window each; channels = upstream area ≥ 1 km²). "
             "Attribution: Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018, provided under COPERNICUS by the EU and ESA.", ""]
    desc = df[["elev_m", "slope_deg", "tri_m", "twi", "spi", "hand_m", "dist_channel_m", "relief_1km_m", "slope_mean_1km_deg"]].describe().T[["mean", "min", "50%", "max"]].round(2)
    lines += [desc.to_markdown(), ""]
    if old is not None:
        m = df.merge(old, on="station")
        if len(m):
            lines += [f"Check against the Terrarium DEM used until now ({len(m)} gauges): elevation r = {m['elev_m'].corr(m['terrain_elev_m']):.3f}, "
                      f"median |difference| = {(m['elev_m'] - m['terrain_elev_m']).abs().median():.1f} m; slope r = {m['slope_deg'].corr(m['terrain_slope_deg']):.3f} "
                      "(slope differs more because GLO-30 is 30 m against ~38 m and is computed with the Horn method here).", ""]
    lines += [f"`upstream_truncated` = True for {int(df['upstream_truncated'].sum())} gauges (their river drains in from outside the window; basin area comes with HydroSHEDS).", ""]
    (OUT / "terrain_at_gauges.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
