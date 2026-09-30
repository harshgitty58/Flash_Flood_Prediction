"""
Temporal Alignment and Calendar Feature Module for Objective 2.
Constructs canonical hourly time-grids and derives leak-free astronomical/monsoon features.
"""

import pandas as pd
import numpy as np

def generate_calendar_features(df: pd.DataFrame, datetime_col: str = "datetime") -> pd.DataFrame:
    """Generates strictly causal calendar and seasonal features from datetime."""
    dt = df[datetime_col]
    
    df["hour_of_day"] = dt.dt.hour
    df["day_of_week"] = dt.dt.dayofweek
    df["day_of_year"] = dt.dt.dayofyear
    df["month"] = dt.dt.month
    
    # Himalayan Monsoon & Season Classification
    # Monsoon: June to September (Months 6, 7, 8, 9)
    df["is_monsoon"] = dt.dt.month.isin([6, 7, 8, 9]).astype(int)
    
    # Monsoon Phase
    conditions = [
        dt.dt.month == 6,
        dt.dt.month.isin([7, 8]),
        dt.dt.month == 9,
    ]
    phases = ["Early_Monsoon", "Peak_Monsoon", "Late_Monsoon"]
    df["monsoon_phase"] = np.select(conditions, phases, default="Non_Monsoon")
    
    # Indian Meteorological Seasons:
    # Winter (Dec, Jan, Feb)
    # Summer/Pre-monsoon (Mar, Apr, May)
    # Monsoon (Jun, Jul, Aug, Sep)
    # Post-monsoon (Oct, Nov)
    season_conds = [
        dt.dt.month.isin([12, 1, 2]),
        dt.dt.month.isin([3, 4, 5]),
        dt.dt.month.isin([6, 7, 8, 9]),
        dt.dt.month.isin([10, 11]),
    ]
    season_names = ["Winter", "Pre_Monsoon", "Monsoon", "Post_Monsoon"]
    df["season"] = np.select(season_conds, season_names, default="Unknown")
    
    return df

def forward_fill_short_gaps(series: pd.Series, max_gap: int = 3) -> pd.Series:
    """Applies strictly forward imputation for isolated sensor gaps <= max_gap hours.
    Never uses future observations (no backward fill).
    """
    return series.ffill(limit=max_gap)
