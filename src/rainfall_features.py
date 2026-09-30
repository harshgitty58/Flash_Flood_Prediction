"""
Rainfall Feature Engineering Module for Objective 2.
Constructs strictly backward-looking cumulative precipitation, API, and intensity metrics.
"""

import pandas as pd
import numpy as np

def compute_antecedent_precipitation_index(rainfall_series: pd.Series, decay_factor: float = 0.85) -> np.ndarray:
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

def generate_rainfall_features(df: pd.DataFrame) -> pd.DataFrame:
    """Computes backward-looking rolling sums, maximums, and API per station."""
    # Ensure sorted by station and datetime
    df = df.sort_values(by=["station", "datetime"]).reset_index(drop=True)
    
    # Fill missing values temporarily with 0 for cumulative rolling sums to prevent cascade of NaNs,
    # but track missingness via missing flags
    df["rain_val_filled"] = df["rainfall_clean"].fillna(0.0)
    
    # Group by station to calculate rolling windows
    grouped = df.groupby("station")["rain_val_filled"]
    
    # 1h, 3h, 6h, 12h, 24h, 48h, 72h backward rolling sums
    df["rain_1h"] = df["rain_val_filled"]
    df["rain_3h"] = grouped.rolling(window=3, min_periods=1).sum().reset_index(level=0, drop=True)
    df["rain_6h"] = grouped.rolling(window=6, min_periods=1).sum().reset_index(level=0, drop=True)
    df["rain_12h"] = grouped.rolling(window=12, min_periods=1).sum().reset_index(level=0, drop=True)
    df["rain_24h"] = grouped.rolling(window=24, min_periods=1).sum().reset_index(level=0, drop=True)
    df["rain_48h"] = grouped.rolling(window=48, min_periods=1).sum().reset_index(level=0, drop=True)
    df["rain_72h"] = grouped.rolling(window=72, min_periods=1).sum().reset_index(level=0, drop=True)
    
    # Rolling maximum intensity over 24h
    df["rain_max_intensity_24h"] = grouped.rolling(window=24, min_periods=1).max().reset_index(level=0, drop=True)
    
    # Rain intensity change: current hour minus previous hour
    df["rain_intensity_change_1h"] = df.groupby("station")["rain_val_filled"].diff(1).fillna(0.0)
    
    # Antecedent Precipitation Index (API) per station
    df["api_decay_85"] = df.groupby("station")["rain_val_filled"].transform(
        lambda s: compute_antecedent_precipitation_index(s, decay_factor=0.85)
    )
    
    # Clean up temporary column
    df = df.drop(columns=["rain_val_filled"])
    return df
