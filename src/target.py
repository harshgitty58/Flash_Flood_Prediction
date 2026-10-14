"""
Target Construction and Leakage Validation Module for Objective 2.
Constructs 24-hour forward flood occurrence target and verifies causal integrity.
"""

import pandas as pd
import numpy as np

def v2_inventory(coverage_end: pd.Timestamp, min_confidence: str = "medium") -> pd.DataFrame:
    """Label v2 (LABELS_PLAN.md §5): IMD ∪ SANDRP ∪ situation reports, one row per (district, day), clipped to the
    IMD coverage end so 'no record' keeps meaning 'no flood' only where the official inventory still runs."""
    from src.config import PROJECT_ROOT
    rank = {"low": 0, "medium": 1, "high": 2}
    d = pd.read_csv(PROJECT_ROOT / "data/external/labels/labels_daily.csv", parse_dates=["date"])
    d = d[(d["date_confidence"].map(rank) >= rank[min_confidence]) & (d["date"] <= coverage_end)]
    return d.drop_duplicates(["district", "date"]).rename(columns={"date": "start_datetime"})[["district", "start_datetime"]]


def construct_flood_target_24h(base_df: pd.DataFrame, flood_inventory_df: pd.DataFrame,
                               coverage_end: pd.Timestamp | None = None) -> pd.DataFrame:
    """Labels y(t) = 1 if a flood is recorded in the station's district on t's calendar day or the next day, else 0."""
    flood_events = flood_inventory_df.dropna(subset=["start_datetime"]).copy()
    
    # The inventory only has event DATES (stored as 00:00). A "next 24 h from t" window therefore labelled the day
    # *before* each flood and left the flood day itself (when the rain falls) as 0. With day-resolution labels the
    # honest target is: a flood is recorded in this district on t's calendar day or the next one.
    targets = np.zeros(len(base_df), dtype=float)
    day = base_df["datetime"].dt.normalize().values.astype("datetime64[D]")
    for district, group in flood_events.groupby("district"):
        ev = np.unique(group["start_datetime"].values.astype("datetime64[D]"))
        m = (base_df["district"] == district).to_numpy()
        d = day[m]
        targets[m] = (np.isin(d, ev) | np.isin(d + np.timedelta64(1, "D"), ev)).astype(float)

    base_df["flood_event_24h"] = np.array(targets, dtype=float)
    # The inventory has no records after its last event, so a 0 there means "unknown", not "no flood".
    # Rows whose 24 h window extends past the coverage end are left unlabelled (NaN): they are excluded
    # from training/evaluation and only used for inference/replay.
    # Labels are known only while the window (today + tomorrow) lies inside the inventory's coverage.
    coverage_end = np.datetime64((coverage_end or flood_events["start_datetime"].max()).normalize(), "D")
    unlabelled = day + np.timedelta64(1, "D") > coverage_end
    base_df.loc[unlabelled, "flood_event_24h"] = np.nan
    base_df["label_available"] = ~unlabelled
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
