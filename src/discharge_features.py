"""
River Discharge Feature Engineering Module for Objective 2.
Constructs backward-looking delta rates, rolling hydrological statistics, and discharge anomalies.
"""

import pandas as pd
import numpy as np

def generate_discharge_features(df: pd.DataFrame) -> pd.DataFrame:
    """Computes backward-looking discharge delta, rolling mean/max, and station anomalies."""
    df = df.sort_values(by=["station", "datetime"]).reset_index(drop=True)
    
    # Backward changes
    df["discharge_change_1h"] = df.groupby("station")["discharge_clean"].diff(1)
    df["discharge_change_3h"] = df.groupby("station")["discharge_clean"].diff(3)
    df["discharge_change_6h"] = df.groupby("station")["discharge_clean"].diff(6)
    
    # Rolling 24h stats
    grouped = df.groupby("station")["discharge_clean"]
    df["rolling_mean_discharge_24h"] = grouped.rolling(window=24, min_periods=1).mean().reset_index(level=0, drop=True)
    df["rolling_max_discharge_24h"] = grouped.rolling(window=24, min_periods=1).max().reset_index(level=0, drop=True)
    
    # Historical station baseline mean for anomaly calculation
    station_means = df.groupby("station")["discharge_clean"].transform("mean")
    df["discharge_anomaly"] = df["discharge_clean"] - station_means
    
    return df
