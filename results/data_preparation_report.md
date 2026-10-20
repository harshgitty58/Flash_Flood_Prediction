# Objective 2: Data Preparation & Transformation Technical Report

> **Historical report (Objective 2 stage, September 2026).** Several figures below were superseded by later data fixes (timestamp parsing, offline-gauge handling, label join, duplicate station-hours). Current values: 518,304 station-hours, 44 rain gauges, labels to 2023-08-26, splits train < 2023-07-01 / validation July 2023 / test 1–25 Aug 2023. See `results/splits.json`, `web/public/data/model.json` and `results/phase4_report.md`.


**Project Title:** Evaluating Multi-Source Data Fusion and Uncertainty in Hyper-Local Flash-Flood Prediction for Hilly Regions of India  
**Study Region:** Uttarakhand, India  
**Objective:** Objective 2 — Data Transformation, Cleaning, Alignment, Normalization, and Feature Engineering  
**Status:** Completed & Validated

---

## 1. Executive Summary

This report documents the end-to-end data transformation pipeline converting raw multi-source hydrological, meteorological, and geospatial observations into a unified, leak-free, ML-ready spatiotemporal dataset for flash-flood prediction in Uttarakhand.

All operations strictly adhered to the requirements established in [`ANTIGRAVITY_OBJECTIVE_2_GUIDELINES.md`](file:///e:/Harsh/VIT/TY/Sem%20V/DS/Course%20Project/Project/ANTIGRAVITY_OBJECTIVE_2_GUIDELINES.md):
* **Zero Target Leakage**: Backward-looking rolling windows only. Historical hazard exposure constructed exclusively from events preceding prediction time $t$.
* **No Artificial Imputation**: Sensor failures and negative readings flagged explicitly (`negative_invalid`, `missing`) without blanket `fillna(0)` zero-substitution.
* **Geographical Integrity**: Preserved district-level precision for historical disaster records rather than fabricating artificial point coordinates.
* **Chronological Splitting**: train < 2023-07-01, validation July 2023, held-out test 1–25 Aug 2023 (labels end 2023-08-26; later hours are unlabelled replay), so no future data reaches the past (see `results/splits.json`).

---

## 2. Source Datasets & Cleaning Ledger

| Dataset Source | Input File | Raw Records | Cleaned Records | Key Cleaning & Normalization Operations |
| :--- | :--- | :--- | :--- | :--- |
| **CWC Telemetry Rainfall** | `rainfall_tel_hr_uttarakhand_uk_2021_2025.csv`<br>`rainfall_tel_hr_uttarakhand_uk_2026_2030.csv` | 46,381 | 21,464 | Standardized timestamp format (`DD-MM-YYYY HH.MM` $\rightarrow$ ISO datetime); floored to hourly resolution; deduplicated on `(station, datetime)`; flagged 43 negative records as `negative_invalid` (set to `NaN`, not 0); mapped 13 district names. |
| **CWC River Discharge** | `cwc_uttarakhand_river_discharge_curated_hourly.csv` | 90,304 | 90,303 | Preserved `discharge_raw`; created `discharge_clean`; filtered negative and high sentinel values using `discharge_quality_flag`; mapped districts. |
| **GSI Landslide Inventory** | `uttarakhand_landslide_inventory_cleaned.csv` | 5,444 | 5,417 | Filtered valid coordinates within Uttarakhand bounding box (Lat: 28.5°–31.5°N, Lon: 77.5°–81.1°E); parsed movement history and year. |
| **Historical Flood Inventory** | `uttarakhand_flood_inventory_curated.csv` | 122 events | 334 district-events | Standardized start/end dates; normalized multi-district entries into one-to-many district mappings; preserved narratives, damages, and fatalities without fabricating point coordinates. |
| **District Context Datasets** | `uttarakhand_dfsi_curated.csv`<br>`uttarakhand_flooded_area_curated.csv`<br>`uttarakhand_flood_impact_curated.csv` | 13 districts | 13 districts | Resolved naming discrepancies (`Hardwar` $\rightarrow$ `Haridwar`, preserved regional `Garhwal`); merged DFSI, corrected % flooded area, fatalities, and population. Preserved missing flood duration for Almora as `NaN`. |

---

## 3. Master District Harmonization Crosswalk

A reusable master mapping table was established at [`data/processed/reference/uttarakhand_district_mapping.csv`](file:///e:/Harsh/VIT/TY/Sem%20V/DS/Course%20Project/Project/data/processed/reference/uttarakhand_district_mapping.csv):
* Standardized 13 official districts: *Almora, Bageshwar, Chamoli, Champawat, Dehradun, Haridwar, Nainital, Pauri Garhwal, Pithoragarh, Rudraprayag, Tehri Garhwal, Udham Singh Nagar, Uttarkashi*.
* Handled spelling variations: `Hardwar` $\rightarrow$ `Haridwar`, `Uttar Kashi Kashi` $\rightarrow$ `Uttarkashi`, `Bageshwari` $\rightarrow$ `Bageshwar`.
* Preserved broad regional administrative aggregates (`Garhwal`) as `Garhwal (Regional)` without false subdivision.

---

## 4. Spatiotemporal Feature Engineering Dictionary

The assembled dataset contains **42 columns** structured at the canonical observation grain of **1 Station $\times$ 1 Hourly Timestamp**:

### A. Rainfall Features (Backward-Looking Only)
* `rain_1h`: Hourly rainfall observation ($mm$).
* `rain_3h`, `rain_6h`, `rain_12h`, `rain_24h`, `rain_48h`, `rain_72h`: Backward rolling cumulative rainfall sums.
* `rain_max_intensity_24h`: Maximum 1-hour rainfall observed in the preceding 24 hours.
* `rain_intensity_change_1h`: Hourly change in rainfall intensity ($P_t - P_{t-1}$).
* `api_decay_85`: Antecedent Precipitation Index computed with exponential memory decay ($k = 0.85$):
  $$API_t = API_{t-1} \cdot 0.85 + P_t$$

### B. Hydrological River Discharge Features
* `discharge_clean`: Clean river discharge in $m^3/s$.
* `discharge_change_1h`, `discharge_change_3h`: 1-hour and 3-hour discharge rates of change.
* `discharge_anomaly`: Departure from the station's historical mean discharge ($Q_t - \bar{Q}_{\text{station}}$).

### C. Spatial Landslide Proximity & Hazard Density
* `dist_to_nearest_landslide_km`: Great-circle Haversine distance from monitoring station to the closest GSI historical landslide.
* `landslide_count_5km`: Number of historical landslides within a 5 km radius.
* `landslide_count_10km`: Number of historical landslides within a 10 km radius.
* `is_landslide_hotspot`: Binary flag indicating $\ge 5$ historical landslides within 10 km.

### D. District Vulnerability Metrics
* `district_flood_severity_index`: Historical flood severity score (DFSI).
* `district_flooded_area_pct`: Satellite-derived percentage flooded area with permanent water body correction.
* `district_historical_fatalities`: Total historical flood casualties in district.
* `district_population`: Census population of district.
* `district_mean_flood_duration_days`: Average duration of historical flood events.

### E. Calendar & Himalayan Monsoon Features
* `hour_of_day` ($0–23$), `day_of_week` ($0–6$), `day_of_year` ($1–366$), `month` ($1–12$).
* `is_monsoon`: Binary flag ($1$ for June–September, $0$ otherwise).
* `monsoon_phase`: Categorical phase (`Early_Monsoon`, `Peak_Monsoon`, `Late_Monsoon`, `Non_Monsoon`).
* `season`: Season category (`Winter`, `Pre_Monsoon`, `Monsoon`, `Post_Monsoon`).

### F. Historical Flood Exposure (Past-Only)
* `historical_flood_count_prior_t`: Cumulative count of flood disaster events in the district occurring strictly prior to timestamp $t$.
* `days_since_last_flood_prior_t`: Elapsed days since the most recent recorded flood in that district prior to $t$.

---

## 5. Target Definition & Leakage Validation

### Primary Target: `flood_event_24h`
Defined as:
$$y(t) = \begin{cases} 1 & \text{if a documented flood begins in the station's district within } [t, t + 24\text{ hours}] \\ 0 & \text{otherwise} \end{cases}$$

### Leakage Verification Check
An automated assertion test was performed on the pipeline:
1. Rolling rainfall, discharge deltas, and historical event counts at cutoff $t$ were evaluated on the full dataset.
2. The dataset was truncated at $t$, discarding all rows $> t$.
3. Features recomputed on the truncated slice matched the original values exactly ($\Delta < 10^{-5}$), confirming **zero future data leakage**.

---

## 6. Chronological Partitioning for Objective 3

To prevent temporal leakage in later model evaluations, the dataset is pre-partitioned:
* **`train`** (Timestamps $< 2025-01-01$): **14,610 rows** (66.5%)
* **`test`** (Timestamps $\ge 2025-01-01$): **7,372 rows** (33.5%)

> **Handoff Rule for Objective 3:** All standardizers, scalers (e.g. `StandardScaler`, `RobustScaler`), and imputation transformers must be fitted **only on the `train` partition** and applied to the `test` partition.

---

## 7. Deliverable Artifacts

1. **Cleaned Datasets**: `data/processed/cleaned/*.parquet`
2. **Master District Crosswalk**: `data/processed/reference/uttarakhand_district_mapping.csv`
3. **Engineered Feature Tables**: `data/processed/features/*.parquet`
4. **Final ML Dataset**:
   * Parquet: `data/processed/final/uttarakhand_flash_flood_ml_dataset.parquet` (7.8 MB)
   * CSV: `data/processed/final/uttarakhand_flash_flood_ml_dataset.csv` (7.5 MB)
5. **Interactive Notebooks**:
   * `notebooks/01_data_audit.ipynb`
   * `notebooks/02_cleaning_validation.ipynb`
   * `notebooks/03_spatiotemporal_alignment.ipynb`
   * `notebooks/04_feature_engineering_target.ipynb`
6. **Data Audit Deliverables**:
   * `results/data_audit/rainfall_audit.csv`
   * `results/data_audit/discharge_audit.csv`
   * `results/data_audit/landslide_audit.csv`
   * `results/data_audit/flood_inventory_audit.csv`
   * `results/data_audit/district_flood_audit.csv`
   * `results/data_audit/summary.md`
