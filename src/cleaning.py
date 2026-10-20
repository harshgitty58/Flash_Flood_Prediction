"""
Cleaning and Source Normalization Module for Objective 2.
Applies domain-specific cleaning, quality-flagging, timestamp parsing, and district harmonization.
Exports cleaned parquets to data/processed/cleaned/.
"""

import pandas as pd
import numpy as np
import re
from pathlib import Path
from src.config import (
    CLEANED_DIR,
    RAINFALL_2021_2025_FILE,
    RAINFALL_2026_2030_FILE,
    DISCHARGE_HOURLY_FILE,
    LANDSLIDE_FILE,
    FLOOD_INVENTORY_FILE,
    DFSI_FILE,
    FLOODED_AREA_FILE,
    FLOOD_IMPACT_FILE,
    UTTARAKHAND_BOUNDS,
)
from src.district_mapping import standardize_district_name
from src.params import P

def parse_cwc_timestamp(s: pd.Series) -> pd.Series:
    """Parses CWC timestamp string formatted typically as 'DD-MM-YYYY HH.MM' into datetime."""
    # Convert '05-10-2022 10.00' -> '05-10-2022 10:00:00'. Hours 0-9 come without a leading zero
    # ('06-10-2022 0.00'); a two-digit-only pattern silently dropped ~47 % of all rows.
    cleaned = s.astype(str).str.strip().str.replace(
        r'\s(\d{1,2})\.(\d{2})$', lambda m: f" {int(m.group(1)):02d}:{m.group(2)}:00", regex=True)
    return pd.to_datetime(cleaned, format='%d-%m-%Y %H:%M:%S', errors='coerce')

SENTINEL_MM = P["qc"]["rain_error_code_mm"]
MAX_PLAUSIBLE_MM_HR = P["qc"]["rain_max_mm_h"]
FAULTY_SHARE = P["qc"]["faulty_share"]
FAULTY_MM_HR = P["qc"]["faulty_mm_h"]
DISCHARGE_MAX_M3S = P["qc"]["discharge_max_m3s"]


def clean_rainfall_data() -> pd.DataFrame:
    """Cleans and standardizes CWC hourly telemetry rainfall."""
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    df1 = pd.read_csv(RAINFALL_2021_2025_FILE)
    df2 = pd.read_csv(RAINFALL_2026_2030_FILE)
    df = pd.concat([df1, df2], ignore_index=True)
    
    # 1. Parse timestamps
    df["datetime"] = parse_cwc_timestamp(df["Data Acquisition Time"])
    
    # Round/floor to nearest hour to maintain canonical hourly grid
    df["datetime"] = df["datetime"].dt.floor("h")
    
    # Drop records with invalid timestamps if any
    df = df.dropna(subset=["datetime"]).copy()
    
    # 2. Standardize column names
    df = df.rename(columns={
        "Station": "station",
        "Latitude": "latitude",
        "Longitude": "longitude",
        "District": "district_raw",
        "Telemetry Hourly Rainfall (mm)": "rainfall_raw",
    })
    
    # 3. Standardize district
    df["district"] = df["district_raw"].apply(standardize_district_name)
    
    # 4. Numeric conversion & Quality flagging
    df["rainfall_raw"] = pd.to_numeric(df["rainfall_raw"], errors="coerce")
    
    # Faulty-gauge quarantine: a station whose non-sentinel readings exceed 100 mm/h more than FAULTY_SHARE
    # of the time is reporting garbage (e.g. Yamuna Colony: median 272 mm/h).
    r = df["rainfall_raw"]
    non_sentinel = r.where((r >= 0) & (r != SENTINEL_MM))
    share_over_100 = (non_sentinel > FAULTY_MM_HR).groupby(df["station"]).mean()
    faulty = set(share_over_100[share_over_100 > FAULTY_SHARE].index)

    conditions = [
        r.isna(),
        r < 0,
        r == SENTINEL_MM,                  # 511.5 = telemetry error code
        df["station"].isin(faulty),
        r > MAX_PLAUSIBLE_MM_HR,           # > 150 mm in one hour: beyond credible gauge readings
        r >= 0,
    ]
    flags = ["missing", "negative_invalid", "sentinel", "faulty_station", "implausible", "valid"]
    df["rainfall_quality_flag"] = np.select(conditions, flags, default="unknown")
    print("Rainfall quality flags:", df["rainfall_quality_flag"].value_counts().to_dict())
    print("Quarantined (faulty) gauges:", sorted(faulty))

    # Clean modelling variable: anything not 'valid' is NaN (never 0)
    df["rainfall_clean"] = r.where(df["rainfall_quality_flag"] == "valid")
    
    # 5. Handle duplicate (station, datetime) records
    # Rule: Keep max valid observation or first non-null
    df = df.sort_values(by=["station", "datetime", "rainfall_clean"], ascending=[True, True, False])
    df = df.drop_duplicates(subset=["station", "datetime"], keep="first").reset_index(drop=True)
    
    # Select key columns
    cols = [
        "station",
        "district",
        "latitude",
        "longitude",
        "datetime",
        "rainfall_raw",
        "rainfall_clean",
        "rainfall_quality_flag",
    ]
    df = df[cols]
    
    output_path = CLEANED_DIR / "rainfall_cleaned.parquet"
    df.to_parquet(output_path, index=False)
    print(f"Cleaned rainfall saved: {len(df):,} records at {output_path}")
    return df

def clean_discharge_data() -> pd.DataFrame:
    """Cleans and standardizes CWC hourly river discharge data."""
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(DISCHARGE_HOURLY_FILE)
    
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df = df.dropna(subset=["datetime"]).copy()
    
    df["district"] = df["district"].apply(standardize_district_name)
    
    df = df.rename(columns={"discharge_m3s": "discharge_raw"})
    df["discharge_raw"] = pd.to_numeric(df["discharge_raw"], errors="coerce")
    
    # Quality flagging
    conditions = [
        df["discharge_raw"].isna(),
        df["discharge_raw"] < 0,
        df["discharge_raw"] > DISCHARGE_MAX_M3S,  # Extreme sentinel/high flood limit
        df["discharge_raw"] >= 0,
    ]
    flags = [
        "missing",
        "negative_invalid",
        "high_sentinel",
        "valid",
    ]
    df["discharge_quality_flag"] = np.select(conditions, flags, default="unknown")
    
    df["discharge_clean"] = df["discharge_raw"].copy()
    df.loc[df["discharge_quality_flag"].isin(["negative_invalid", "missing", "high_sentinel"]), "discharge_clean"] = np.nan
    
    df = df.sort_values(by=["station", "datetime"]).drop_duplicates(subset=["station", "datetime"]).reset_index(drop=True)
    
    output_path = CLEANED_DIR / "discharge_cleaned.parquet"
    df.to_parquet(output_path, index=False)
    print(f"Cleaned river discharge saved: {len(df):,} records at {output_path}")
    return df

def clean_landslide_data() -> pd.DataFrame:
    """Cleans historical landslide inventory from GSI."""
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(LANDSLIDE_FILE)
    
    df["district"] = df["district"].apply(standardize_district_name)
    
    # Filter valid coordinates in Uttarakhand
    valid_coords = (
        (df["latitude"] >= UTTARAKHAND_BOUNDS["lat_min"]) &
        (df["latitude"] <= UTTARAKHAND_BOUNDS["lat_max"]) &
        (df["longitude"] >= UTTARAKHAND_BOUNDS["lon_min"]) &
        (df["longitude"] <= UTTARAKHAND_BOUNDS["lon_max"])
    )
    df = df[valid_coords].copy()
    
    # Extract year if present in material_movement_history_raw
    def extract_year(text):
        if not isinstance(text, str):
            return np.nan
        m = re.search(r'(19\d{2}|20\d{2})', text)
        return int(m.group(1)) if m else np.nan
        
    df["slide_year"] = df["material_movement_history_raw"].apply(extract_year)
    
    output_path = CLEANED_DIR / "landslide_cleaned.parquet"
    df.to_parquet(output_path, index=False)
    print(f"Cleaned landslides saved: {len(df):,} records at {output_path}")
    return df

def clean_flood_inventory_data() -> pd.DataFrame:
    """Cleans historical flood disaster inventory without fabricating point coordinates."""
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(FLOOD_INVENTORY_FILE)
    
    df["start_datetime"] = pd.to_datetime(df["Start_Date"], errors="coerce")
    df["end_datetime"] = pd.to_datetime(df["End_Date"], errors="coerce")
    df["duration_days"] = pd.to_numeric(df["Duration_Days"], errors="coerce")
    
    # Standardize district strings and explode multi-district events for mapping
    mapping_rows = []
    for _, row in df.iterrows():
        raw_dists = str(row.get("Districts", "")).split(",")
        for d in raw_dists:
            std_d = standardize_district_name(d)
            if std_d != "Unknown":
                mapping_rows.append({
                    "uei": row.get("UEI"),
                    "start_datetime": row.get("start_datetime"),
                    "end_datetime": row.get("end_datetime"),
                    "duration_days": row.get("duration_days"),
                    "main_cause": row.get("Main Cause"),
                    "district": std_d,
                    "fatalities": row.get("Human fatality"),
                    "injured": row.get("Human injured"),
                    "extent_damage": row.get("Extent of damage"),
                })
                
    df_clean = pd.DataFrame(mapping_rows).drop_duplicates()
    output_path = CLEANED_DIR / "flood_inventory_cleaned.parquet"
    df_clean.to_parquet(output_path, index=False)
    print(f"Cleaned flood inventory saved: {len(df_clean):,} district-event records at {output_path}")
    return df_clean

def clean_district_supporting_data() -> pd.DataFrame:
    """Merges DFSI, flooded area, and flood impact by standard district."""
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    
    df_dfsi = pd.read_csv(DFSI_FILE)
    df_dfsi["district"] = df_dfsi["District"].apply(standardize_district_name)
    df_dfsi = df_dfsi[["district", "DFSI"]].drop_duplicates(subset=["district"])
    
    df_area = pd.read_csv(FLOODED_AREA_FILE)
    df_area["district"] = df_area["District"].apply(standardize_district_name)
    df_area = df_area[["district", "Corrected_Percent_Flooded_Area"]].drop_duplicates(subset=["district"])
    
    df_impact = pd.read_csv(FLOOD_IMPACT_FILE)
    df_impact["district"] = df_impact["District"].apply(standardize_district_name)
    df_impact = df_impact[["district", "Human_fatality", "Population", "Mean_Flood_Duration"]].drop_duplicates(subset=["district"])
    
    # Merge on standard district
    merged = df_dfsi.merge(df_area, on="district", how="outer")
    merged = merged.merge(df_impact, on="district", how="outer")
    
    # Rename columns cleanly
    merged = merged.rename(columns={
        "DFSI": "district_flood_severity_index",
        "Corrected_Percent_Flooded_Area": "district_flooded_area_pct",
        "Human_fatality": "district_historical_fatalities",
        "Population": "district_population",
        "Mean_Flood_Duration": "district_mean_flood_duration_days",
    })
    
    output_path = CLEANED_DIR / "district_supporting_cleaned.parquet"
    merged.to_parquet(output_path, index=False)
    print(f"Cleaned district supporting data saved: {len(merged):,} districts at {output_path}")
    return merged

def run_all_cleaning():
    """Executes all data cleaning routines."""
    clean_rainfall_data()
    clean_discharge_data()
    clean_landslide_data()
    clean_flood_inventory_data()
    clean_district_supporting_data()
    print("All datasets cleaned and stored in data/processed/cleaned/.")

if __name__ == "__main__":
    run_all_cleaning()
