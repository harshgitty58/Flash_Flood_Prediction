"""
End-to-End ML-Ready Dataset Assembly Pipeline for Objective 2.
Coordinates cleaning, alignment, feature engineering, target labeling, and chronological split.
Exports final dataset to data/processed/final/.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from src.config import (
    CLEANED_DIR,
    ALIGNED_DIR,
    FEATURES_DIR,
    TARGETS_DIR,
    FINAL_DIR,
    FINAL_PARQUET_FILE,
    FINAL_CSV_FILE,
    ensure_directories,
)
from src.district_mapping import generate_master_mapping_csv
from src.cleaning import run_all_cleaning
from src.temporal import generate_calendar_features
from src.spatial import compute_station_landslide_features
from src.rainfall_features import generate_rainfall_features
from src.discharge_features import generate_discharge_features
from src.flood_features import compute_historical_flood_features
from src.target import construct_flood_target_24h, verify_zero_future_leakage

def run_objective_2_pipeline() -> pd.DataFrame:
    """Executes the complete Objective 2 data transformation and feature engineering pipeline."""
    ensure_directories()
    
    print("\n--- 1. Generating Master District Crosswalk ---")
    generate_master_mapping_csv()
    
    print("\n--- 2. Executing Source Data Cleaning ---")
    run_all_cleaning()
    
    print("\n--- 3. Ingesting Cleaned Sources ---")
    rain_df = pd.read_parquet(CLEANED_DIR / "rainfall_cleaned.parquet")
    discharge_df = pd.read_parquet(CLEANED_DIR / "discharge_cleaned.parquet")
    landslide_df = pd.read_parquet(CLEANED_DIR / "landslide_cleaned.parquet")
    flood_inv_df = pd.read_parquet(CLEANED_DIR / "flood_inventory_cleaned.parquet")
    district_df = pd.read_parquet(CLEANED_DIR / "district_supporting_cleaned.parquet")
    
    print("\n--- 4. Computing Rainfall Features (Backward Rolling & API) ---")
    rain_feat = generate_rainfall_features(rain_df)
    
    print("\n--- 5. Computing Discharge Features (Deltas & Anomalies) ---")
    dis_feat = generate_discharge_features(discharge_df)
    
    # Save intermediate features
    rain_feat.to_parquet(FEATURES_DIR / "rainfall_features.parquet", index=False)
    dis_feat.to_parquet(FEATURES_DIR / "discharge_features.parquet", index=False)
    
    print("\n--- 6. Constructing Spatial Landslide Proximity & Density ---")
    station_landslides = compute_station_landslide_features(rain_df, landslide_df)
    station_landslides.to_parquet(FEATURES_DIR / "station_landslide_features.parquet", index=False)
    
    print("\n--- 7. Assembling Master Spatiotemporal Base Table ---")
    # Base grain is Station x Hourly Timestamp from rainfall stations
    base = rain_feat.copy()
    
    # Merge spatial landslide features
    base = base.merge(
        station_landslides[["station", "dist_to_nearest_landslide_km", "landslide_count_5km", "landslide_count_10km", "is_landslide_hotspot"]],
        on="station",
        how="left"
    )
    
    # Merge district-level hazard metrics
    base = base.merge(
        district_df,
        on="district",
        how="left"
    )
    
    # Optional join for hydrological river discharge where station names match or nearest river station
    # Discharge has 7 stations; we attach nearest river discharge or district discharge
    # Map river discharge by district or matching station
    dis_district = dis_feat.groupby(["district", "datetime"])[["discharge_clean", "discharge_change_1h", "discharge_change_3h", "discharge_anomaly"]].mean().reset_index()
    base = base.merge(
        dis_district,
        on=["district", "datetime"],
        how="left"
    )
    
    print("\n--- 8. Generating Calendar and Monsoon Features ---")
    base = generate_calendar_features(base, datetime_col="datetime")
    
    print("\n--- 9. Computing Past-Only Historical Flood Exposure ---")
    base = compute_historical_flood_features(base, flood_inv_df)
    
    print("\n--- 10. Constructing 24h Forward Target & Checking Leakage ---")
    base = construct_flood_target_24h(base, flood_inv_df)
    verify_zero_future_leakage(base)
    
    print("\n--- 11. Defining Chronological Train/Test Partition ---")
    # Train on earlier records (before 2025-01-01), test on 2025+ holdout
    base["split_partition"] = np.where(base["datetime"] < pd.to_datetime("2025-01-01"), "train", "test")
    
    # Export Final ML-Ready Datasets
    print("\n--- 12. Exporting Final ML-Ready Table ---")
    base.to_parquet(FINAL_PARQUET_FILE, index=False)
    
    # Also export CSV for presentation and inspection
    base.to_csv(FINAL_CSV_FILE, index=False)
    
    print(f"\nSUCCESS! Master ML Dataset saved:")
    print(f"Parquet: {FINAL_PARQUET_FILE} ({base.shape[0]:,} rows x {base.shape[1]} columns)")
    print(f"CSV:     {FINAL_CSV_FILE}")
    print(f"Train rows: {(base['split_partition'] == 'train').sum():,}")
    print(f"Test rows:  {(base['split_partition'] == 'test').sum():,}")
    print(f"Target distribution (flood_event_24h = 1): {(base['flood_event_24h'] == 1).sum():,} records")
    
    return base

if __name__ == "__main__":
    run_objective_2_pipeline()
