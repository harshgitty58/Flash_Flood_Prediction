"""
Data Loading and Feature-Group Definitions for Phase 3.
Provides controlled feature subsets for Experiments A through E.
"""

import pandas as pd
from typing import Dict, List, Tuple
from src.config import FINAL_PARQUET_FILE
from src.model_config import TARGET_COL

# Explicit Feature Families
RAINFALL_FEATURES = [
    "rain_1h",
    "rain_3h",
    "rain_6h",
    "rain_12h",
    "rain_24h",
    "rain_48h",
    "rain_72h",
    "rain_max_intensity_24h",
    "rain_intensity_change_1h",
    "api_decay_85",
]

DISCHARGE_FEATURES = [
    "discharge_clean",
    "discharge_change_1h",
    "discharge_change_3h",
    "discharge_anomaly",
]

HISTORICAL_FLOOD_FEATURES = [
    "historical_flood_count_prior_t",
    "days_since_last_flood_prior_t",
    "district_flood_severity_index",
    "district_flooded_area_pct",
    "district_historical_fatalities",
    "district_population",
    "district_mean_flood_duration_days",
]

LANDSLIDE_FEATURES = [
    "dist_to_nearest_landslide_km",
    "landslide_count_5km",
    "landslide_count_10km",
    "is_landslide_hotspot",
]

TEMPORAL_SPATIAL_FEATURES = [
    "hour_of_day",
    "day_of_week",
    "day_of_year",
    "month",
    "is_monsoon",
    "latitude",
    "longitude",
]

# Controlled Experiment Feature Groups
FEATURE_EXPERIMENTS: Dict[str, List[str]] = {
    "Exp_A_Rainfall_Only": RAINFALL_FEATURES,
    "Exp_B_Rainfall_Discharge": RAINFALL_FEATURES + DISCHARGE_FEATURES,
    "Exp_C_Rainfall_Discharge_FloodHist": (
        RAINFALL_FEATURES + DISCHARGE_FEATURES + HISTORICAL_FLOOD_FEATURES
    ),
    "Exp_D_Rainfall_Discharge_Flood_Landslide": (
        RAINFALL_FEATURES + DISCHARGE_FEATURES + HISTORICAL_FLOOD_FEATURES + LANDSLIDE_FEATURES
    ),
    "Exp_E_Full_Multimodal": (
        RAINFALL_FEATURES + DISCHARGE_FEATURES + HISTORICAL_FLOOD_FEATURES + LANDSLIDE_FEATURES + TEMPORAL_SPATIAL_FEATURES
    ),
    # Exp E without raw latitude/longitude: tests whether the model generalises beyond memorising flood locations.
    "Exp_F_No_Location": (
        RAINFALL_FEATURES + DISCHARGE_FEATURES + HISTORICAL_FLOOD_FEATURES + LANDSLIDE_FEATURES
        + [f for f in TEMPORAL_SPATIAL_FEATURES if f not in ("latitude", "longitude")]
    ),
}

# Exp D without the two time-varying history counters. They drift without bound once the flood inventory stops
# (2023-08), so replay-period predictions extrapolated; the static district susceptibility indices are kept.
FEATURE_EXPERIMENTS["Exp_G_Static_History"] = [
    f for f in FEATURE_EXPERIMENTS["Exp_D_Rainfall_Discharge_Flood_Landslide"]
    if f not in ("days_since_last_flood_prior_t", "historical_flood_count_prior_t")
]

# Phase 2/3 external + relative features (src/enrich_features.py)
ERA5_FEATURES = ["era5_1h", "era5_3h", "era5_6h", "era5_24h", "era5_72h", "era5_max_1h_24h"]
SOIL_FEATURES = ["sm_0_7", "sm_7_28", "sm_anom"]
RELATIVE_FEATURES = ["pct_rain_24h", "pct_era5_24h", "pct_rain_72h", "z_rain_24h_month", "agree_log_ratio", "agree_both_wet"]
TERRAIN_FEATURES = ["terrain_elev_m", "terrain_slope_deg", "terrain_relief_2km_m", "terrain_tpi_1km_m"]
DYNAMIC_FEATURES = RAINFALL_FEATURES + DISCHARGE_FEATURES + ERA5_FEATURES + SOIL_FEATURES + RELATIVE_FEATURES

# H: G + second rain source + soil moisture + station-relative rain + terrain
FEATURE_EXPERIMENTS["Exp_H_Multisource"] = (FEATURE_EXPERIMENTS["Exp_G_Static_History"] + ERA5_FEATURES + SOIL_FEATURES
                                            + RELATIVE_FEATURES + TERRAIN_FEATURES)
# T: trigger-only (dynamic signals, no district constants) — tests whether the data can predict *when*
FEATURE_EXPERIMENTS["Exp_T_Trigger_Only"] = DYNAMIC_FEATURES

# Feature set used for the final tuned models and all downstream outputs.
# Chosen by leave-one-event-out CV (src/event_cv.py): best pooled ROC-AUC, no coordinates, no drifting counters.
FINAL_EXPERIMENT = "Exp_G_Static_History"

def load_ml_dataset() -> pd.DataFrame:
    """Loads the final ML-ready dataset produced in Objective 2."""
    df = pd.read_parquet(FINAL_PARQUET_FILE)
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df.sort_values(by=["station", "datetime"]).reset_index(drop=True)

def get_features_and_target(df: pd.DataFrame, experiment_name: str = "Exp_E_Full_Multimodal") -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    """Extracts features X and target y for a specific controlled experiment."""
    feature_cols = FEATURE_EXPERIMENTS[experiment_name]
    X = df[feature_cols].copy()
    y = df[TARGET_COL].copy()
    return X, y, feature_cols
