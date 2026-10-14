"""
Historical Flood Exposure Feature Module for Objective 2.
Ensures zero data leakage: computes past-only flood metrics strictly prior to timestamp t.
"""

import pandas as pd
import numpy as np

def compute_historical_flood_features(base_df: pd.DataFrame, flood_inventory_df: pd.DataFrame) -> pd.DataFrame:
    """Computes past-only cumulative flood event count and days since last flood per district."""
    # Ensure datetime format
    flood_events = flood_inventory_df.dropna(subset=["start_datetime"]).sort_values("start_datetime").copy()
    
    # Vectorised. Events have day resolution, so only floods on EARLIER calendar days count as history:
    # counting an event dated today (00:00) from 01:00 onwards would leak the label.
    counts_before_t = np.zeros(len(base_df), dtype=int)
    days_since_last = np.full(len(base_df), np.nan)
    dts = base_df["datetime"].values.astype("datetime64[ns]")
    for district, group in flood_events.groupby("district"):
        ev = np.sort(group["start_datetime"].values.astype("datetime64[ns]"))
        m = (base_df["district"] == district).to_numpy()
        t = dts[m]
        cnt = np.searchsorted(ev, t.astype("datetime64[D]").astype("datetime64[ns]"), side="left")
        counts_before_t[m] = cnt
        last = ev[np.maximum(cnt - 1, 0)]
        days_since_last[m] = np.where(cnt > 0, np.round((t - last) / np.timedelta64(1, "D"), 1), np.nan)

    base_df["historical_flood_count_prior_t"] = counts_before_t
    base_df["days_since_last_flood_prior_t"] = days_since_last
    return base_df
