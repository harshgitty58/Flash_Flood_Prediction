"""
Configuration module for Uttarakhand Flash-Flood Prediction (Objective 2).
Defines workspace paths, spatial/temporal parameters, and coordinate bounding boxes.
"""

from pathlib import Path

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CURATED_DATA_DIR = PROJECT_ROOT / "curated_dataset"  # single copy; checked against curated_dataset/MANIFEST.sha256
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
RESULTS_DIR = PROJECT_ROOT / "results"
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"

# Subdirectories in processed data
REF_DIR = PROCESSED_DIR / "reference"
CLEANED_DIR = PROCESSED_DIR / "cleaned"
ALIGNED_DIR = PROCESSED_DIR / "aligned"
FEATURES_DIR = PROCESSED_DIR / "features"
TARGETS_DIR = PROCESSED_DIR / "targets"
FINAL_DIR = PROCESSED_DIR / "final"
AUDIT_DIR = RESULTS_DIR / "data_audit"

# Source File Paths
RAINFALL_2021_2025_FILE = CURATED_DATA_DIR / "cwc_rainfall_uttarakhand" / "rainfall_tel_hr_uttarakhand_uk_2021_2025.csv"
RAINFALL_2026_2030_FILE = CURATED_DATA_DIR / "cwc_rainfall_uttarakhand" / "rainfall_tel_hr_uttarakhand_uk_2026_2030.csv"

DISCHARGE_CLEANED_FILE = CURATED_DATA_DIR / "river_discharge" / "cwc_uttarakhand_river_discharge_cleaned.csv"
DISCHARGE_HOURLY_FILE = CURATED_DATA_DIR / "river_discharge" / "cwc_uttarakhand_river_discharge_curated_hourly.csv"
DISCHARGE_SUMMARY_FILE = CURATED_DATA_DIR / "river_discharge" / "cwc_uttarakhand_river_station_summary.csv"

LANDSLIDE_FILE = CURATED_DATA_DIR / "landslide" / "uttarakhand_landslide_inventory_cleaned.csv"

FLOOD_INVENTORY_FILE = CURATED_DATA_DIR / "flood_inventory" / "uttarakhand_flood_inventory_curated.csv"
DFSI_FILE = CURATED_DATA_DIR / "flood_inventory" / "uttarakhand_dfsi_curated.csv"
FLOODED_AREA_FILE = CURATED_DATA_DIR / "flood_inventory" / "uttarakhand_flooded_area_curated.csv"
FLOOD_IMPACT_FILE = CURATED_DATA_DIR / "flood_inventory" / "uttarakhand_flood_impact_curated.csv"

# Destination Master Files
DISTRICT_MAPPING_FILE = REF_DIR / "uttarakhand_district_mapping.csv"
FINAL_PARQUET_FILE = FINAL_DIR / "uttarakhand_flash_flood_ml_dataset.parquet"
FINAL_CSV_FILE = FINAL_DIR / "uttarakhand_flash_flood_ml_dataset.csv"

# Geographic & Coordinate Bounds for Uttarakhand
UTTARAKHAND_BOUNDS = {
    "lat_min": 28.5,
    "lat_max": 31.5,
    "lon_min": 77.5,
    "lon_max": 81.1,
}

# Standardized Timezone
TIMEZONE = "Asia/Kolkata"  # IST (UTC+05:30)

# Canonical 13 Uttarakhand Districts
OFFICIAL_UTTARAKHAND_DISTRICTS = [
    "Almora",
    "Bageshwar",
    "Chamoli",
    "Champawat",
    "Dehradun",
    "Haridwar",
    "Nainital",
    "Pauri Garhwal",
    "Pithoragarh",
    "Rudraprayag",
    "Tehri Garhwal",
    "Udham Singh Nagar",
    "Uttarkashi",
]

def ensure_directories():
    """Ensure all required project subdirectories exist."""
    for d in [
        DATA_DIR,
        PROCESSED_DIR,
        REF_DIR,
        CLEANED_DIR,
        ALIGNED_DIR,
        FEATURES_DIR,
        TARGETS_DIR,
        FINAL_DIR,
        RESULTS_DIR,
        AUDIT_DIR,
        NOTEBOOKS_DIR,
    ]:
        d.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    ensure_directories()
    print("Project directories initialized successfully.")
