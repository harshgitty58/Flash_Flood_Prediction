# Antigravity Agent Brief — Uttarakhand Flash-Flood Prediction
## Objective 2: Data Transformation, Cleaning and Normalization

> **Status:** Objective 1 — Dataset Curation and Multi-Source Integration — is complete.
>
> **Current task:** Implement Objective 2 only. Do **not** start model training yet.

---

# 1. Project Overview

## Project Title

**Evaluating Multi-Source Data Fusion and Uncertainty in Hyper-Local Flash-Flood Prediction for Hilly Regions of India**

## Initial Study Region

**Uttarakhand, India**

The project specification defines the first version as Uttarakhand, with possible future expansion to Sikkim and Himachal Pradesh.

## Core Research Problem

Build a multi-source, uncertainty-aware flash-flood early-warning framework that combines environmental, hydrological, and historical hazard information. The intended system ultimately predicts flood occurrence, estimates prediction uncertainty, and supports interpretable warning levels.

The primary target specified in the project plan is:

> **Flood event within the next 24 hours**

A secondary target is:

> **Flood severity**

The project also intends to study how missing/noisy observations affect predictions and how well a model generalizes across locations and time periods.

---

# 2. FINALIZED PROJECT OBJECTIVES

These are the four objectives that must be preserved exactly in the project documentation.

## Objective 1 — Dataset Curation and Multi-Source Integration

Curate and integrate heterogeneous datasets from **rainfall, soil moisture, river discharge, terrain, flood history, and landslide records** to create a unified, geographically and temporally aligned dataset for Uttarakhand flash-flood prediction.

## Objective 2 — Data Transformation, Cleaning and Normalization

Perform **data cleaning, missing-value handling, outlier detection, normalization, feature transformation, spatial-temporal alignment, and feature engineering** to convert raw multi-source data into a consistent ML-ready dataset.

## Objective 3 — Optimized Multi-Model Training and Evaluation

Develop and compare multiple ML models such as **Logistic Regression, Random Forest, and XGBoost**, using **optimized training, hyperparameter tuning, efficient feature selection, and rigorous train/test validation** to identify reliable prediction models.

## Objective 4 — Uncertainty-Aware and Robust Flood Prediction

Enhance the selected model with **uncertainty estimation and robustness analysis**, evaluating prediction reliability under **missing, noisy, or degraded observations** and translating the results into practical early-warning levels.

---

# 3. WHAT OBJECTIVE 1 HAS ALREADY ACCOMPLISHED

The datasets were collected and organized before starting Objective 2.

Current usable/collected sources include:

### A. CWC Hourly Rainfall — Uttarakhand

Use the larger CWC rainfall file as the main rainfall source.

Known characteristics of the current file:

- 37,410 records
- 47 stations
- 13 Uttarakhand districts
- latitude/longitude available
- hourly timestamp field
- rainfall field in millimetres

Important: there is also a 4-row rainfall sample file from an earlier inspection. **Do not use the 4-row sample as the project's main rainfall dataset.**

### B. CWC River Discharge — Uttarakhand

Available files include:

- Full cleaned discharge data
- Curated hourly discharge data
- Station summary

The curated hourly discharge file is the preferred ML working source.

The original discharge data contained:

- missing discharge observations
- negative values
- extreme/sentinel-like values

These must be handled carefully rather than silently deleting them.

### C. India Flood Inventory — Uttarakhand

A curated Uttarakhand event-level flood inventory has been prepared.

Approximate coverage:

- 121 Uttarakhand event records
- historical coverage from 1970–2023
- event dates are available
- district/event descriptions are available
- many historical records do not contain point coordinates

This source is important for constructing the flood target and historical flood features.

### D. Historical Landslide Inventory — Uttarakhand

A cleaned Uttarakhand landslide inventory has been extracted.

Approximate size:

- 5,443 extracted records
- latitude/longitude available
- district information
- movement/material/history information

It can later be transformed into spatial historical-landslide features.

### E. District-Level Flood Supporting Data

Three curated district-level datasets are available:

1. District Flood Severity Index (DFSI)
2. Corrected Percentage Flooded Area
3. Flood impacts:
   - human fatality
   - human injured
   - population
   - mean flood duration

These are supporting historical/contextual variables and should not be treated as hourly observations.

### F. LULC

LULC has been requested from Bhuvan and may become available later.

**Do not block Objective 2 waiting for LULC.**

### G. Skipped Sources

The following were intentionally skipped for now:

- MOSDAC soil moisture
- DEM/terrain download
- Flood Hazard Zone layer
- Temperature

Do not fabricate or simulate these missing datasets.

If a dataset is unavailable, document that limitation.

---

# 4. OBJECTIVE 2 — WHAT MUST BE DONE

Objective 2 is not just "clean the CSVs."

The purpose is to transform multiple heterogeneous sources into a **single consistent spatiotemporal ML-ready table**, while preserving traceability to the source data.

The workflow must be:

```text
Raw / Curated Source Files
        ↓
Data Audit
        ↓
Cleaning
        ↓
Missing-Value Handling
        ↓
Outlier / Invalid-Value Handling
        ↓
Timestamp Standardization
        ↓
Spatial Standardization
        ↓
Temporal Alignment
        ↓
Spatial Alignment
        ↓
Historical Feature Construction
        ↓
Rainfall / Discharge Feature Engineering
        ↓
Target Construction
        ↓
Leakage Checks
        ↓
Train/Test-Aware Transformation
        ↓
Final ML-Ready Dataset
```

---

# 5. REQUIRED OBJECTIVE 2 DELIVERABLES

Antigravity must produce all of the following.

## Deliverable 1 — Data Audit

Create a machine-readable and human-readable data audit for every source.

For each dataset report:

- row count
- column count
- column names
- data types
- missing values
- duplicate records
- date range
- number of stations/districts
- coordinate availability
- invalid numeric values
- suspicious/extreme values
- categorical inconsistencies
- source-specific problems

Output:

```text
results/data_audit/
    rainfall_audit.csv
    discharge_audit.csv
    flood_inventory_audit.csv
    landslide_audit.csv
    district_flood_audit.csv
```

Also create:

```text
results/data_audit/summary.md
```

---

# 6. RAINFALL CLEANING

Use the larger CWC Uttarakhand hourly rainfall dataset.

## Required operations

### Timestamp

Convert:

```text
Data Acquisition Time
```

to a proper datetime field.

Standardize it to one documented timezone convention.

Do not silently alter timestamps.

### Rainfall

Convert rainfall to numeric.

Check:

- missing values
- negative rainfall
- physically implausible values
- duplicate station/timestamp combinations

Negative rainfall values must not automatically be interpreted as zero.

They should be treated as invalid/missing unless the source documentation proves otherwise.

### Station identity

Preserve:

- station name
- district
- latitude
- longitude

Do not merge two stations merely because their names look similar.

### Duplicate records

For duplicate station/timestamp combinations:

1. inspect whether coordinates differ
2. inspect whether rainfall values differ
3. determine whether duplicate rows represent different station coordinates, duplicated observations, or conflicting records
4. document the rule used to resolve them

Do not arbitrarily keep the first row without analysis.

---

# 7. RIVER DISCHARGE CLEANING

Use the curated hourly CWC discharge dataset as the primary modelling input, while keeping the full cleaned source as an audit/archive.

Required checks:

- timestamp validity
- station identity
- coordinate validity
- missing discharge
- negative discharge
- extreme/sentinel values
- duplicate station/timestamp combinations

For negative/extreme discharge observations:

- investigate first
- mark them with a quality flag
- do not treat obviously invalid negative values as genuine river discharge
- do not silently delete the source record
- create a cleaned modelling value separately from the raw/source value

Recommended fields:

```text
discharge_raw
discharge_clean
discharge_quality_flag
```

Useful derived hydrological features include:

- discharge change over 1 hour
- discharge change over 3 hours
- discharge change over 6 hours
- rolling mean discharge
- rolling maximum discharge
- discharge anomaly

These are explicitly part of the project's planned feature set.

---

# 8. FLOOD INVENTORY CLEANING

The flood inventory is event-level and historical.

Required:

- standardize start date
- standardize end date
- validate duration
- standardize district names
- preserve original event ID/UEI
- preserve source description
- preserve impact information
- distinguish single-district events from multi-district events

## CRITICAL: do not create false precision

If an event has no latitude/longitude, do not invent coordinates.

If an event covers several districts, retain the relationship.

If district-level mapping is required, create one-to-many event-to-district records rather than assigning a fake single coordinate.

---

# 9. LANDSLIDE CLEANING

Required:

- latitude/longitude validation
- valid geographic range checks
- district-name standardization
- duplicate detection
- date/history parsing where reliable
- movement/material normalization where possible

Do not infer an event date when the source does not provide one.

The landslide dataset will later support features such as:

- historical landslide count
- landslide density
- distance to nearest historical landslide
- landslide hotspot indicator

The project specification explicitly lists these as candidate historical-landslide features.

---

# 10. DISTRICT-LEVEL FLOOD DATA

The DFSI, flooded-area, and flood-impact files are district-level data.

Standardize district names across all files before merging.

Examples that must be harmonized consistently:

```text
Hardwar → Haridwar
UDHAM SINGH NAGAR → Udham Singh Nagar
PAURI GARHWAL → Pauri Garhwal
```

However:

> **Do not invent a more specific district when the source only says "Garhwal".**

Preserve the source meaning and document the limitation.

Do not treat missing mean flood duration as zero.

Do not turn missing values into fabricated measurements.

---

# 11. DISTRICT NAME MASTER MAPPING

Create one reusable master mapping table.

Output:

```text
data/processed/reference/uttarakhand_district_mapping.csv
```

Recommended columns:

```text
source_name
standard_district
source_dataset
mapping_status
notes
```

This mapping must be used consistently everywhere.

Do not duplicate spelling-cleaning logic in multiple notebooks.

---

# 12. TEMPORAL ALIGNMENT

This is one of the most important parts of Objective 2.

The model is intended to operate at an hourly temporal scale because rainfall and river-discharge inputs are hourly.

Create a canonical hourly timeline.

Recommended conceptual key:

```text
location/station + datetime
```

All time-varying observations should be aligned to this timeline.

## Important rule

Do not use future observations to fill earlier timestamps.

For example:

- forward-filling may be acceptable under a documented sensor-gap rule for selected environmental variables
- backward-filling from the future is dangerous for forecasting and should not be used unless scientifically justified and explicitly documented

All imputation decisions must be recorded.

---

# 13. SPATIAL ALIGNMENT

The project is intended to be geographically aligned.

Available spatial keys include:

- station
- latitude
- longitude
- district

Use coordinates wherever they are available.

The integration strategy should be based on the spatial resolution of each source.

Examples:

### Station-level data

Rainfall and river discharge can remain associated with their station coordinates.

### District-level data

DFSI, flooded-area and flood-impact variables can be joined by standardized district.

### Historical landslides

Use coordinates for spatial feature construction.

### Historical floods

Use district membership and event dates when coordinates are unavailable.

Do not pretend that a district-level observation is a precise station-level observation.

---

# 14. TARGET CONSTRUCTION

The project specification defines:

> **Flood event within next 24 hours (primary target)**

The modelling dataset therefore needs a clearly documented forecasting label.

A defensible implementation is:

```text
y(t) = 1
if a relevant flood event is scheduled/recorded to begin within the next 24 hours
else
y(t) = 0
```

But the exact event-to-location matching rule must be documented.

Because the historical flood inventory includes multi-day events and multi-district events, Antigravity must explicitly define:

- what constitutes event onset
- which district/station is affected
- how multi-district events are represented
- how a long-running flood event affects future timestamps
- how events with missing spatial precision are handled

**Do not label the same timestamp using information that would not have been known at prediction time.**

---

# 15. HISTORICAL FEATURE LEAKAGE RULE

This is critical.

Historical flood and landslide features must only use information available **before the prediction timestamp**.

Examples:

Correct:

```text
historical_flood_count_before_t
days_since_last_flood_before_t
historical_landslide_count_before_t
```

Incorrect:

```text
historical_flood_count_using_entire_dataset
```

because that would include future events.

For each timestamp `t`, calculate historical statistics from data available before `t`.

This is required for a valid forecasting experiment.

---

# 16. RAINFALL FEATURE ENGINEERING

The project specification explicitly includes:

- rainfall 1 hour
- rainfall 3 hours
- rainfall 6 hours
- rainfall 12 hours
- rainfall 24 hours
- rainfall 48 hours
- rainfall 72 hours
- maximum rainfall intensity
- rainfall intensity change
- Antecedent Precipitation Index (API)
- hours since rainfall started
- hours since heavy rainfall started

Objective 2 should construct these where the available data supports them.

All rolling windows must be **backward-looking** relative to prediction time.

Example:

At time `t`:

```text
rain_3h(t)
```

must summarize rainfall observed during the preceding 3-hour window, not the next 3 hours.

---

# 17. DISCHARGE FEATURE ENGINEERING

Construct where data coverage supports it:

```text
discharge
discharge_change_1h
discharge_change_3h
discharge_change_6h
rolling_mean_discharge
rolling_max_discharge
discharge_anomaly
```

All features must be backward-looking.

Do not use future discharge values.

---

# 18. LANDSLIDE FEATURE ENGINEERING

Where valid coordinates and dates support it, create:

```text
historical_landslide_count
landslide_density_5km
landslide_density_10km
distance_to_nearest_historical_landslide
historical_landslide_hotspot
landslide_prone_indicator
```

If an event lacks a usable date, it can still contribute to static historical spatial density, but it must not be used as if its occurrence date were known.

Document the distinction between:

```text
static historical spatial feature
```

and:

```text
time-dependent historical feature
```

---

# 19. FLOOD HISTORY FEATURES

The project specification includes:

```text
historical_flood_count
flood_frequency_5y
flood_frequency_10y
days_since_last_flood
historical_flood_severity
historical_flooded_area
district_flood_severity_index
historical_flood_hotspot
```

Implement only the features that can be justified by the available sources.

Again:

> Historical features must use only information available before the prediction timestamp.

---

# 20. TEMPORAL FEATURES

Create where appropriate:

```text
hour_of_day
day_of_week
day_of_year
month
season
monsoon_indicator
monsoon_phase
```

These are based on the timestamp itself and therefore do not create future leakage.

---

# 21. MISSING-VALUE HANDLING

Missing-value treatment must be **feature-specific**.

Do not simply run:

```python
df.fillna(0)
```

over the entire integrated dataset.

Examples:

- Missing rainfall ≠ zero rainfall
- Missing discharge ≠ zero discharge
- Missing flood duration ≠ zero duration
- Missing historical event count may have different semantics depending on the feature definition

Use explicit strategies and quality flags.

Recommended:

```text
<feature>_missing_flag
```

where missingness itself may carry useful information.

For time-series variables, distinguish:

- isolated missing observation
- short sensor gap
- long outage
- station not yet operational

---

# 22. OUTLIER DETECTION

Perform outlier detection separately by variable and, where appropriate, by station.

Do not globally remove observations simply because they are statistically extreme.

For example, a genuine extreme rainfall event may be exactly the observation the model needs to learn from.

The workflow should distinguish:

```text
measurement error
```

from:

```text
rare but plausible extreme event
```

Use source documentation/physical plausibility where possible.

For every correction/removal:

```text
what was changed
why
how many records
```

must be recorded.

---

# 23. NORMALIZATION

Normalization must be done correctly for ML.

Recommended sequence:

```text
split data into train/validation/test
        ↓
fit scaler on TRAIN ONLY
        ↓
transform validation/test using the same fitted scaler
```

Never fit a scaler on the full dataset before splitting.

This would leak information from the test period into training.

For models such as:

- Logistic Regression

scaling is generally useful.

Tree-based models such as:

- Random Forest
- XGBoost

do not require the same normalization assumptions, but a consistent preprocessing framework can still be maintained.

Keep the preprocessing objects with the experiment so the same transformation can be reproduced later.

---

# 24. TRAIN/TEST SPLIT REQUIREMENT

Because this is a forecasting problem, do **not** use a random row-wise train/test split as the only evaluation design.

At minimum, Objective 2 should prepare for a chronological split:

```text
Earlier period → training
Later period   → testing
```

The project plan explicitly includes temporal generalization:

> train on earlier years and test on future years.

This should prevent future information from entering the training set.

---

# 25. FEATURE DATASET DESIGN

The final modelling table should have one clearly defined observation grain.

Recommended initial grain:

```text
one station/location × one hourly timestamp
```

Conceptually:

```text
station_id
datetime
latitude
longitude
district
rainfall features...
discharge features...
historical flood features...
historical landslide features...
temporal features...
target
```

Do not create multiple rows for the same station/timestamp after integration unless there is a scientifically documented reason.

---

# 26. RECOMMENDED OUTPUT STRUCTURE

Create:

```text
Dataset/
└── curated_dataset/
    ├── rainfall/
    ├── river_discharge/
    ├── flood_inventory/
    ├── landslide_inventory/
    └── reference/
```

For Objective 2, create a separate processed area:

```text
Dataset/
└── processed/
    ├── cleaned/
    ├── aligned/
    ├── features/
    ├── targets/
    └── final/
```

Recommended final outputs:

```text
Dataset/processed/cleaned/
    rainfall_cleaned.parquet
    discharge_cleaned.parquet
    flood_inventory_cleaned.parquet
    landslide_cleaned.parquet

Dataset/processed/aligned/
    integrated_hourly_base.parquet

Dataset/processed/features/
    rainfall_features.parquet
    discharge_features.parquet
    historical_flood_features.parquet
    historical_landslide_features.parquet

Dataset/processed/targets/
    flood_24h_target.parquet

Dataset/processed/final/
    uttarakhand_flash_flood_ml_dataset.parquet
    uttarakhand_flash_flood_ml_dataset.csv
```

Parquet is preferred internally for larger datasets; CSV can be generated as a shareable/export format.

---

# 27. CODE ORGANIZATION

Do not put the entire pipeline in one giant notebook.

Recommended:

```text
src/
├── config.py
├── io.py
├── validation.py
├── cleaning.py
├── temporal.py
├── spatial.py
├── rainfall_features.py
├── discharge_features.py
├── flood_features.py
├── landslide_features.py
├── target.py
└── pipeline.py
```

Recommended notebooks:

```text
notebooks/
├── 01_data_audit.ipynb
├── 02_cleaning_validation.ipynb
├── 03_spatiotemporal_alignment.ipynb
└── 04_feature_engineering.ipynb
```

The notebooks should demonstrate the work.

The reusable logic should live in `src/`.

---

# 28. REPRODUCIBILITY

Every transformation must be reproducible.

Record:

- source filename
- source date/range where available
- transformation performed
- rows before
- rows after
- missing values before/after
- invalid values detected
- duplicate rows detected/resolved
- feature definitions
- target definition
- train/test date boundaries
- preprocessing parameters

Create:

```text
results/data_preparation_report.md
```

This report should explain exactly what changed from the source datasets to the final ML dataset.

---

# 29. DATA QUALITY CHECKS BEFORE OBJECTIVE 2 IS MARKED COMPLETE

The agent must verify all of the following:

### Schema

- [ ] expected columns exist
- [ ] numeric fields are numeric
- [ ] timestamps parse correctly

### Spatial

- [ ] latitude ∈ [-90, 90]
- [ ] longitude ∈ [-180, 180]
- [ ] Uttarakhand district names are standardized

### Temporal

- [ ] timestamps are sorted
- [ ] timezone convention is documented
- [ ] duplicate station/timestamp observations are resolved
- [ ] no future information enters backward-looking features

### Numeric quality

- [ ] invalid negative rainfall handled
- [ ] invalid negative discharge handled
- [ ] extreme/sentinel discharge values handled
- [ ] missing values documented

### Historical feature quality

- [ ] flood history is calculated using only past information
- [ ] landslide history is calculated using only information available at the prediction timestamp when time-dependent
- [ ] district-level historical features are not constructed using future data

### ML readiness

- [ ] final observation grain is documented
- [ ] target is defined
- [ ] target leakage checks completed
- [ ] preprocessing is reproducible
- [ ] chronological train/test boundary is documented

---

# 30. WHAT NOT TO DO

Antigravity must **not**:

1. Start model training as part of Objective 2.
2. Randomly delete rows without recording why.
3. Replace every missing value with zero.
4. Treat every statistical outlier as an error.
5. Use future observations in rolling features.
6. Use full-dataset historical counts that include future events.
7. Fit normalization/scaling on the complete dataset before splitting.
8. Invent coordinates for events that have none.
9. Invent missing event dates.
10. Wait indefinitely for skipped datasets such as soil moisture or DEM.
11. Fabricate data for unavailable sources.
12. Modify the original curated source files in place.
13. Build separate, inconsistent district-name cleaning logic in multiple notebooks.

---

# 31. OBJECTIVE 2 DEFINITION OF DONE

Objective 2 is complete only when:

```text
Raw/curated source data
        ↓
audited
        ↓
cleaned
        ↓
validated
        ↓
spatially aligned
        ↓
temporally aligned
        ↓
feature engineered
        ↓
target constructed
        ↓
leakage checked
        ↓
train/test-aware transformations prepared
        ↓
final ML-ready dataset exported
        ↓
data preparation report generated
```

The final output should be a **single reproducible ML-ready Uttarakhand flash-flood dataset** plus the intermediate datasets and documentation required to trace every transformation.

---

# 32. IMPORTANT RESEARCH CONTEXT

The project specification identifies candidate inputs across rainfall, soil moisture, terrain, hydrology, historical floods, landslides, meteorology, temporal variables, and spatial variables. It also defines the primary target as a flood event within the next 24 hours and lists uncertainty/confidence interval as a model output.

The later research stages include:

- multi-source data fusion
- model complexity comparison
- observation degradation experiments
- uncertainty quantification
- spatial generalization
- temporal generalization
- SHAP-based feature attribution
- warning threshold analysis
- lead-time analysis
- robustness × uncertainty analysis

Therefore Objective 2 must produce a dataset and preprocessing pipeline that make those later experiments possible without data leakage.

---

# 33. HANDOFF TO OBJECTIVE 3

At the end of Objective 2, do not tune or select the final model.

The handoff should contain:

```text
final ML dataset
feature dictionary
target definition
train/validation/test time ranges
preprocessing pipeline
missing-value strategy
outlier strategy
spatial alignment strategy
feature-generation definitions
data-quality report
reproducible code
```

Then Objective 3 can independently perform:

```text
Logistic Regression
Random Forest
XGBoost
hyperparameter tuning
feature selection
model evaluation
```

and compare them using the predefined validation strategy.
