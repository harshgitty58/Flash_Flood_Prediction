"""
Rainfall Feature Engineering Module for Objective 2.
Constructs strictly backward-looking cumulative precipitation, API, and intensity metrics.
"""

import pandas as pd
import numpy as np

from src.params import P

def compute_antecedent_precipitation_index(rainfall_series: pd.Series, decay_factor: float = P["features"]["api_decay_hourly"]) -> np.ndarray:
    """Computes Antecedent Precipitation Index (API): API_t = API_{t-1} * k + P_t."""
    vals = rainfall_series.fillna(0.0).values
    api = np.zeros(len(vals), dtype=np.float64)
    if len(vals) == 0:
        return api
    
    current_api = 0.0
    for i in range(len(vals)):
        current_api = current_api * decay_factor + vals[i]
        api[i] = current_api
    return np.round(api, 3)

OFFLINE_GAP_MONSOON_H = P["qc"]["offline_gap_monsoon_h"]   # Jun-Sep: a week without any rain record = gauge offline
OFFLINE_GAP_DRY_H = P["qc"]["offline_gap_dry_h"]           # other months: dry spells are long, so allow 45 days


def to_hourly_grid(df: pd.DataFrame) -> pd.DataFrame:
    """Expand each station to a complete hourly series between its first and last record.

    CWC telemetry files only list hours with non-zero rain (minimum 0.5 mm, no zeros), so an absent hour means
    0 mm. Hours flagged invalid stay NaN. Stations with no valid reading at all (quarantined gauges) are dropped.
    """
    meta = (df.groupby(["station", "district", "latitude", "longitude"]).size().rename("n").reset_index()
            .sort_values("n", ascending=False).drop_duplicates("station").drop(columns="n").set_index("station"))
    parts = []
    for st, g in df.groupby("station"):
        if g["rainfall_clean"].notna().sum() == 0:
            print(f"  dropping {st}: no valid readings (quarantined gauge)")
            continue
        g = g.set_index("datetime")
        idx = pd.date_range(g.index.min(), g.index.max(), freq="h")
        out = pd.DataFrame(index=idx)
        out["rainfall_clean"] = g["rainfall_clean"].reindex(idx)
        out["rainfall_quality_flag"] = g["rainfall_quality_flag"].reindex(idx).fillna("no_record_dry")
        out.loc[out["rainfall_quality_flag"] == "no_record_dry", "rainfall_clean"] = 0.0
        # A long silence is an outage, not a dry spell: hours inside gaps longer than the season's limit are dropped
        # (station not reporting), so a dead gauge never looks like a confidently dry one.
        rec = g.index.to_series()
        gap_h = rec.diff().dt.total_seconds().div(3600)
        limit = np.where(rec.dt.month.isin([6, 7, 8, 9]), OFFLINE_GAP_MONSOON_H, OFFLINE_GAP_DRY_H)
        offline = pd.Series(False, index=idx)
        for end, h in gap_h[gap_h > limit].items():
            offline.loc[end - pd.Timedelta(hours=h - 1): end - pd.Timedelta(hours=1)] = True
        out = out[~offline.to_numpy()]
        out["station"] = st
        parts.append(out.rename_axis("datetime").reset_index())
    grid = pd.concat(parts, ignore_index=True).join(meta, on="station")
    return grid[["station", "district", "latitude", "longitude", "datetime", "rainfall_clean", "rainfall_quality_flag"]]


def generate_rainfall_features(df: pd.DataFrame) -> pd.DataFrame:
    """Computes backward-looking rolling sums, maximums, and API per station on a complete hourly grid,
    so the row windows are true clock-hour windows (rain_24h = last 24 hours, not last 24 rainy readings)."""
    df = to_hourly_grid(df)
    df = df.sort_values(by=["station", "datetime"]).reset_index(drop=True)
    
    # Fill missing values temporarily with 0 for cumulative rolling sums to prevent cascade of NaNs,
    # but track missingness via missing flags
    df["rain_val_filled"] = df["rainfall_clean"].fillna(0.0)
    
    # Group by station to calculate rolling windows
    grouped = df.groupby("station")["rain_val_filled"]
    
    # 1h, 3h, 6h, 12h, 24h, 48h, 72h backward rolling sums
    df["rain_1h"] = df["rain_val_filled"]
    # Time-based windows ("24h" = last 24 clock hours): the grid has holes where a gauge was offline,
    # so row counts would reach back across an outage.
    ts = df.set_index("datetime").groupby("station")["rain_val_filled"]
    for h in (3, 6, 12, 24, 48, 72):
        df[f"rain_{h}h"] = ts.rolling(f"{h}h", min_periods=1).sum().to_numpy()

    # Rolling maximum intensity over 24h
    df["rain_max_intensity_24h"] = ts.rolling("24h", min_periods=1).max().to_numpy()
    
    # Rain intensity change: current hour minus previous hour
    df["rain_intensity_change_1h"] = df.groupby("station")["rain_val_filled"].diff(1).fillna(0.0)
    
    # Antecedent Precipitation Index (API) per station
    df["api_decay_85"] = df.groupby("station")["rain_val_filled"].transform(
        lambda s: compute_antecedent_precipitation_index(s, decay_factor=0.85)
    )
    
    # Clean up temporary column
    df = df.drop(columns=["rain_val_filled"])
    return df
