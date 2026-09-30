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
    
    # Pre-aggregate flood event start times per district
    district_events = {}
    for district, group in flood_events.groupby("district"):
        district_events[district] = group["start_datetime"].values
        
    counts_before_t = []
    days_since_last = []
    
    # Iterate through base records
    for _, row in base_df[["district", "datetime"]].iterrows():
        dist = row["district"]
        dt = row["datetime"]
        
        events = district_events.get(dist)
        if events is None or len(events) == 0:
            counts_before_t.append(0)
            days_since_last.append(np.nan)
            continue
            
        past_events = events[events < np.datetime64(dt)]
        count = len(past_events)
        counts_before_t.append(count)
        
        if count > 0:
            last_event_dt = past_events[-1]
            diff_days = (np.datetime64(dt) - last_event_dt) / np.timedelta64(1, "D")
            days_since_last.append(round(float(diff_days), 1))
        else:
            days_since_last.append(np.nan)
            
    base_df["historical_flood_count_prior_t"] = counts_before_t
    base_df["days_since_last_flood_prior_t"] = days_since_last
    return base_df
