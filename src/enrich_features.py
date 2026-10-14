"""
Phase 2/3 — enrich the hourly table with external data and station-relative normalisation.

Adds (all past-only, fitted on the training period only where a statistic is learned):
  ERA5 / ERA5-Land (Open-Meteo, data/external/era5/):
    era5_1h, era5_3h, era5_6h, era5_24h, era5_72h, era5_max_1h_24h   reanalysis rain over the gauge's grid cell
    sm_0_7, sm_7_28, sm_anom                                         soil moisture + anomaly vs station-month mean
  Station-relative rainfall (removes "100 mm means different things at different gauges"):
    pct_rain_24h, pct_era5_24h, pct_rain_72h   percentile of the value within that station's training distribution
    z_rain_24h_month                           seasonal z-score vs the station's training mean/std for that month
  Source agreement:
    agree_log_ratio   log1p(gauge 24 h) − log1p(ERA5 24 h)
    agree_both_wet    1 if both gauge ≥ 35.5 mm and ERA5 ≥ 15 mm in 24 h
  Terrain at the gauge (AWS Terrarium DEM, zoom 12 ≈ 38 m):
    terrain_elev_m, terrain_slope_deg, terrain_relief_2km_m, terrain_tpi_1km_m (negative = valley bottom)
"""
import io
import math
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from PIL import Image

from src.config import PROJECT_ROOT
from src.model_config import TRAIN_END_DATE

ERA5_DIR = PROJECT_ROOT / "data/external/era5"
DEM_DIR = PROJECT_ROOT / "data/external/dem12"
DEM_Z = 12


# ------------------------------------------------------------------ ERA5
def era5_features() -> pd.DataFrame:
    parts = []
    for f in sorted(ERA5_DIR.glob("*.csv")):
        e = pd.read_csv(f, parse_dates=["datetime"]).sort_values("datetime").set_index("datetime")
        p = e["era5_precip"].fillna(0.0)
        out = pd.DataFrame(index=e.index)
        out["era5_1h"] = p
        for h in (3, 6, 24, 72):
            out[f"era5_{h}h"] = p.rolling(f"{h}h", min_periods=1).sum()
        out["era5_max_1h_24h"] = p.rolling("24h", min_periods=1).max()
        out["sm_0_7"], out["sm_7_28"] = e["sm_0_7"], e["sm_7_28"]
        out["station"] = f.stem
        parts.append(out.reset_index())
    if not parts:
        raise FileNotFoundError("run scripts/fetch_era5.py first")
    return pd.concat(parts, ignore_index=True)


# ------------------------------------------------------------------ terrain
_tiles: dict = {}


def _tile(x: int, y: int) -> np.ndarray:
    if (x, y) not in _tiles:
        p = DEM_DIR / f"{DEM_Z}_{x}_{y}.png"
        if not p.exists():
            DEM_DIR.mkdir(parents=True, exist_ok=True)
            r = requests.get(f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{DEM_Z}/{x}/{y}.png", timeout=60)
            r.raise_for_status()
            p.write_bytes(r.content)
        a = np.asarray(Image.open(io.BytesIO(p.read_bytes())).convert("RGB"), dtype=np.float64)
        _tiles[(x, y)] = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
    return _tiles[(x, y)]


def _window(lat: float, lon: float, half_px: int) -> tuple[np.ndarray, float]:
    """DEM window (2·half+1 px square) centred on the point, stitched across tiles; returns (array, metres/px)."""
    n = 2 ** DEM_Z
    fx = (lon + 180) / 360 * n * 256
    fy = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n * 256
    cx, cy = int(fx), int(fy)
    out = np.empty((2 * half_px + 1, 2 * half_px + 1))
    for dy in range(-half_px, half_px + 1):
        for dx in range(-half_px, half_px + 1):
            px, py = cx + dx, cy + dy
            out[dy + half_px, dx + half_px] = _tile(px // 256, py // 256)[py % 256, px % 256]
    m_per_px = 156543.03 * math.cos(math.radians(lat)) / n
    return out, m_per_px


def terrain_features(stations: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, s in stations.iterrows():
        w, mpp = _window(s.latitude, s.longitude, int(math.ceil(2000 / (156543.03 * math.cos(math.radians(s.latitude)) / 2 ** DEM_Z))))
        c = w.shape[0] // 2
        k1 = max(1, int(round(1000 / mpp)))
        gy, gx = np.gradient(w[c - 1:c + 2, c - 1:c + 2], mpp)
        rows.append({"station": s.station, "terrain_elev_m": round(float(w[c, c]), 1),
                     "terrain_slope_deg": round(float(np.degrees(np.arctan(np.hypot(gx[1, 1], gy[1, 1])))), 2),
                     "terrain_relief_2km_m": round(float(w.max() - w.min()), 1),
                     "terrain_tpi_1km_m": round(float(w[c, c] - w[c - k1:c + k1 + 1, c - k1:c + k1 + 1].mean()), 1)})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ station-relative normalisation
def _percentile_map(train: pd.DataFrame, full: pd.DataFrame, col: str) -> np.ndarray:
    """Percentile of each value within that station's training distribution (past-only fit, train period)."""
    out = np.full(len(full), np.nan)
    ref = {st: np.sort(g[col].dropna().to_numpy()) for st, g in train.groupby("station")}
    allref = np.sort(train[col].dropna().to_numpy())
    for st, idx in full.groupby("station").indices.items():
        r = ref.get(st)
        r = r if r is not None and len(r) > 200 else allref
        out[idx] = np.searchsorted(r, full[col].to_numpy()[idx], side="right") / len(r)
    return out


def enrich(base: pd.DataFrame) -> pd.DataFrame:
    e = era5_features()
    base = base.merge(e, on=["station", "datetime"], how="left")
    train = base[base["datetime"] < pd.Timestamp(TRAIN_END_DATE)]

    # soil-moisture anomaly vs the station's training mean for that calendar month
    sm_ref = train.groupby(["station", train["datetime"].dt.month])["sm_0_7"].mean()
    keys = list(zip(base["station"], base["datetime"].dt.month))
    base["sm_anom"] = base["sm_0_7"].to_numpy() - pd.Series(keys).map(sm_ref).to_numpy()

    for col in ("rain_24h", "era5_24h", "rain_72h"):
        base[f"pct_{col}"] = _percentile_map(train, base, col)
    mstats = train.groupby(["station", train["datetime"].dt.month])["rain_24h"].agg(["mean", "std"])
    mu = pd.Series(keys).map(mstats["mean"]).to_numpy()
    sd = pd.Series(keys).map(mstats["std"]).to_numpy()
    # clipped: in dry months a station's training std is ~0, which would explode the z-score
    base["z_rain_24h_month"] = np.clip((base["rain_24h"].to_numpy() - mu) / np.where(sd > 0.5, sd, np.nan), -5, 20)

    base["agree_log_ratio"] = np.log1p(base["rain_24h"]) - np.log1p(base["era5_24h"])
    base["agree_both_wet"] = ((base["rain_24h"] >= 35.5) & (base["era5_24h"] >= 15)).astype(int)

    st = base.groupby("station")[["latitude", "longitude"]].first().reset_index()
    base = base.merge(terrain_features(st), on="station", how="left")
    return base
