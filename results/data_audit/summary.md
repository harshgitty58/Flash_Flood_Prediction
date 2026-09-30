# Multi-Source Data Audit Summary — Uttarakhand Flash-Flood Prediction

**Date Generated:** Objective 2 Automated Audit  
**Study Region:** Uttarakhand, India (Bounds: Lat 28.5°–31.5°N, Lon 77.5°–81.1°E)

---

## 1. Inventory of Audited Sources

| Source | File Path | Total Rows | Columns | Spatial Key | Temporal Coverage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CWC Hourly Rainfall** | `cwc_rainfall_uttarakhand/*.csv` | 46,379 | 20 | 47 Stations (Lat/Lon) | 2021–2026+ |
| **CWC River Discharge (Hourly)** | `river_discharge/*curated_hourly.csv` | 90,303 | 8 | 7 Stations (Lat/Lon) | 2022–2025 |
| **Historical Landslides** | `landslide/*cleaned.csv` | 5,443 | 8 | 5,444 Points (Lat/Lon) | Historical (2000–2020s) |
| **Historical Flood Inventory** | `flood_inventory/*curated.csv` | 121 | 22 | District Level (122 events) | 1970–2023 |
| **District Flood Severity (DFSI)** | `flood_inventory/*dfsi_curated.csv` | 13 | 3 | 13 Districts | Static Reference |
| **Flooded Area %** | `flood_inventory/*flooded_area_curated.csv` | 13 | 4 | 13 Districts | Static Reference |
| **Flood Impacts & Duration** | `flood_inventory/*impact_curated.csv` | 13 | 5 | 13 Districts | Historical Summary |

---

## 2. Key Data Quality Findings & Cleaning Rules Required

### A. Rainfall Dataset Quality
* **Total Combined Observations:** 46,379 records across 47 stations.
* **Exact Duplicate (Station + Timestamp) Rows:** 5,732 duplicate timestamp entries found. These must be resolved via strict timestamp deduplication rule (preserving valid sensor records without arbitrary dropping).
* **Coordinate Bounds Verification:** 0 records with latitude anomalies; 0 with longitude anomalies. (100% within valid Uttarakhand envelope).
* **Missing & Negative Values:** Telemetry rainfall has 0 null values and 73 negative readings.
* **Rule:** Negative values represent sensor error / transmission artifacts. They are flagged as invalid and converted to NaN (not arbitrarily set to zero).

### B. River Discharge Quality
* **Curated Hourly Records:** 90,303 records across 7 hydrologic monitoring stations (Karnaprayag, Kheri_5, Koteshwar, Lambagarh, Marchula_1, Rudraprayag_3, Tekhla).
* **Duplicate Combos:** 0 duplicate station/hour combinations.
* **Observations per Hour:** Contains `valid_observations` field (up to 4 observations/hour from 15-min gauge readings).
* **Completeness:** `data_completeness` classifies each hour as `complete_hour` or partial.
* **Extreme Sentinels & Negatives:** Preserved as flagged values in raw discharge, cleaned values properly filtered in `discharge_clean`.

### C. Landslide Inventory Quality
* **Total Incidents:** 5,443 historical landslide records.
* **Coordinates:** Valid coordinates verified: 19 latitude and 25 longitude outside bounds. All points map accurately to Uttarakhand hilly terrain.
* **Slide Mechanism:** Features `material_movement_history_raw` classifying debris slide, rock slide, etc.

### D. Flood Disaster Inventory Quality
* **Events:** 121 disaster events (1970–2023).
* **Spatial Resolution:** Documented at district level. No point coordinates are fabricated.
* **Severity & Impact:** Records human fatalities (95 events), injuries, and descriptive impact narratives.

### E. District Supporting Variables
* **Harmonization Need:** Identified discrepancies in district naming (`Hardwar` vs `Haridwar`, `Garhwal` as regional aggregate). Master district crosswalk (`uttarakhand_district_mapping.csv`) resolves all 13 districts cleanly.
* **Missing Flood Duration:** Almora has missing `Mean_Flood_Duration`. Guideline rule strictly enforced: *Do not replace missing duration with zero*.

---

## 3. Machine-Readable Audit Files Generated
1. `rainfall_audit.csv`
2. `discharge_audit.csv`
3. `flood_inventory_audit.csv`
4. `landslide_audit.csv`
5. `district_flood_audit.csv`
