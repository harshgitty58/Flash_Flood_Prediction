"""
District Name Master Mapping Module.
Provides consistent crosswalk across all multi-source Uttarakhand datasets.
Generates data/processed/reference/uttarakhand_district_mapping.csv.
"""

import pandas as pd
from pathlib import Path
from src.config import DISTRICT_MAPPING_FILE, OFFICIAL_UTTARAKHAND_DISTRICTS, REF_DIR

# Master Mapping Dictionary: Clean standardized mapping for variations
DISTRICT_SYNONYMS = {
    # Official districts (identity)
    "almora": "Almora",
    "bageshwar": "Bageshwar",
    "chamoli": "Chamoli",
    "champawat": "Champawat",
    "dehradun": "Dehradun",
    "haridwar": "Haridwar",
    "nainital": "Nainital",
    "pauri garhwal": "Pauri Garhwal",
    "pithoragarh": "Pithoragarh",
    "rudraprayag": "Rudraprayag",
    "tehri garhwal": "Tehri Garhwal",
    "udham singh nagar": "Udham Singh Nagar",
    "uttarkashi": "Uttarkashi",
    
    # Common variations and source spellings
    "hardwar": "Haridwar",
    "uttar kashi": "Uttarkashi",
    "uttar kashi kashi": "Uttarkashi",
    "tehri garhwal ": "Tehri Garhwal",
    "tehri-garhwal": "Tehri Garhwal",
    "pauri": "Pauri Garhwal",
    "garhwal": "Garhwal (Regional)",  # Preserved as per guideline: do not invent specific district
    "bageshwari": "Bageshwar",
    "pithorgarh": "Pithoragarh",
    "u.s. nagar": "Udham Singh Nagar",
    "udhamsingh nagar": "Udham Singh Nagar",
    "udham singh nagar ": "Udham Singh Nagar",
}

def standardize_district_name(raw_name: str) -> str:
    """Standardizes any raw district string into the canonical project representation."""
    if not isinstance(raw_name, str) or not raw_name.strip():
        return "Unknown"
    cleaned = raw_name.strip().lower()
    return DISTRICT_SYNONYMS.get(cleaned, raw_name.strip().title())

def generate_master_mapping_csv() -> pd.DataFrame:
    """Creates the master district mapping reference CSV required by Objective 2."""
    REF_DIR.mkdir(parents=True, exist_ok=True)
    
    records = [
        # Standard districts
        {"source_name": "Almora", "standard_district": "Almora", "source_dataset": "All", "mapping_status": "Exact", "notes": "Official Uttarakhand district"},
        {"source_name": "Bageshwar", "standard_district": "Bageshwar", "source_dataset": "All", "mapping_status": "Exact", "notes": "Official Uttarakhand district"},
        {"source_name": "Chamoli", "standard_district": "Chamoli", "source_dataset": "All", "mapping_status": "Exact", "notes": "Official Uttarakhand district"},
        {"source_name": "Champawat", "standard_district": "Champawat", "source_dataset": "All", "mapping_status": "Exact", "notes": "Official Uttarakhand district"},
        {"source_name": "Dehradun", "standard_district": "Dehradun", "source_dataset": "All", "mapping_status": "Exact", "notes": "Official Uttarakhand district"},
        {"source_name": "Haridwar", "standard_district": "Haridwar", "source_dataset": "All", "mapping_status": "Exact", "notes": "Official Uttarakhand district"},
        {"source_name": "Hardwar", "standard_district": "Haridwar", "source_dataset": "DFSI / Historical", "mapping_status": "Standardized", "notes": "Colonial / alternate spelling of Haridwar"},
        {"source_name": "Nainital", "standard_district": "Nainital", "source_dataset": "All", "mapping_status": "Exact", "notes": "Official Uttarakhand district"},
        {"source_name": "Pauri Garhwal", "standard_district": "Pauri Garhwal", "source_dataset": "All", "mapping_status": "Exact", "notes": "Official Uttarakhand district"},
        {"source_name": "PAURI GARHWAL", "standard_district": "Pauri Garhwal", "source_dataset": "CWC / Inventory", "mapping_status": "Standardized", "notes": "Case normalization"},
        {"source_name": "Garhwal", "standard_district": "Garhwal (Regional)", "source_dataset": "Flood Impact / DFSI", "mapping_status": "Preserved Regional", "notes": "Historical administrative division covering multiple districts; preserved without false precision"},
        {"source_name": "Pithoragarh", "standard_district": "Pithoragarh", "source_dataset": "All", "mapping_status": "Exact", "notes": "Official Uttarakhand district"},
        {"source_name": "Pithorgarh", "standard_district": "Pithoragarh", "source_dataset": "Flood Inventory", "mapping_status": "Standardized", "notes": "Spelling variation"},
        {"source_name": "Rudraprayag", "standard_district": "Rudraprayag", "source_dataset": "All", "mapping_status": "Exact", "notes": "Official Uttarakhand district"},
        {"source_name": "Tehri Garhwal", "standard_district": "Tehri Garhwal", "source_dataset": "All", "mapping_status": "Exact", "notes": "Official Uttarakhand district"},
        {"source_name": "Tehri Garhwal ", "standard_district": "Tehri Garhwal", "source_dataset": "Flood Inventory", "mapping_status": "Standardized", "notes": "Trailing whitespace stripped"},
        {"source_name": "Udham Singh Nagar", "standard_district": "Udham Singh Nagar", "source_dataset": "All", "mapping_status": "Exact", "notes": "Official Uttarakhand district"},
        {"source_name": "UDHAM SINGH NAGAR", "standard_district": "Udham Singh Nagar", "source_dataset": "CWC / Inventory", "mapping_status": "Standardized", "notes": "Case normalization"},
        {"source_name": "Uttarkashi", "standard_district": "Uttarkashi", "source_dataset": "All", "mapping_status": "Exact", "notes": "Official Uttarakhand district"},
        {"source_name": "Uttar Kashi", "standard_district": "Uttarkashi", "source_dataset": "Flood Inventory", "mapping_status": "Standardized", "notes": "Space separated variant"},
        {"source_name": "Uttar Kashi Kashi", "standard_district": "Uttarkashi", "source_dataset": "Flood Inventory", "mapping_status": "Standardized", "notes": "Duplicated name anomaly in IMD historical inventory"},
        {"source_name": "Bageshwari", "standard_district": "Bageshwar", "source_dataset": "Flood Inventory", "mapping_status": "Standardized", "notes": "Tehsil/subdivision reference to Bageshwar"},
    ]
    
    df = pd.DataFrame(records)
    df.to_csv(DISTRICT_MAPPING_FILE, index=False)
    return df

if __name__ == "__main__":
    df = generate_master_mapping_csv()
    print(f"Master district mapping generated at {DISTRICT_MAPPING_FILE} ({len(df)} mappings).")
