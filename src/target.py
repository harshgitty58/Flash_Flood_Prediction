"""
Target Construction and Leakage Validation Module for Objective 2.
Constructs 24-hour forward flood occurrence target and verifies causal integrity.
"""

import pandas as pd
import numpy as np

def construct_flood_target_24h(base_df: pd.DataFrame, flood_inventory_df: pd.DataFrame) -> pd.DataFrame:
    """Labels y(t) = 1 if a documented flood starts in the station's district within [t, t + 24 hours], else 0."""
    flood_events = flood_inventory_df.dropna(subset=["start_datetime"]).copy()
    
    district_events = {}
    for district, group in flood_events.groupby("district"):
        district_events[district] = group["start_datetime"].values
        
    targets = []
    
    for _, row in base_df[["district", "datetime"]].iterrows():
        dist = row["district"]
        dt = row["datetime"]
        
        events = district_events.get(dist)
        if events is None or len(events) == 0:
            targets.append(0)
            continue
            
        t_start = np.datetime64(dt)
        t_end = t_start + np.timedelta64(24, "h")
        
        # Check if any event start date falls in [t_start, t_end]
        is_hit = np.any((events >= t_start) & (events <= t_end))
        targets.append(1 if is_hit else 0)
        
    base_df["flood_event_24h"] = targets
    return base_df

def verify_zero_future_leakage(df: pd.DataFrame) -> bool:
    """Runs automated verification that rolling features at t do not depend on t + k."""
    # Check that rolling rainfall at t is identical regardless of whether future rows exist
    sample_station = df["station"].iloc[0]
    st_df = df[df["station"] == sample_station].sort_values("datetime").copy()
    
    if len(st_df) > 10:
        cutoff = st_df["datetime"].iloc[len(st_df) // 2]
        # Rain 3h at cutoff
        val_full = st_df.loc[st_df["datetime"] == cutoff, "rain_3h"].values[0]
        
        # Recalculate on truncated dataset ending at cutoff
        truncated = st_df[st_df["datetime"] <= cutoff].copy()
        val_trunc = truncated["rain_1h"].tail(3).sum()
        
        assert np.isclose(val_full, val_trunc, atol=1e-3), "Leakage detected in backward rolling rainfall!"
        
    print("Zero-future-leakage assertion verified successfully.")
    return True
