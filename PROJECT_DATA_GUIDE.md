# PRAHAR: Project Guide for the Machine-Learning Work

**Multi-source, uncertainty-aware flash-flood early warning for Uttarakhand**
*Predict · Prepare · Protect*

| | |
|---|---|
| Course | Data Science, TY Semester V, VIT |
| Repository | https://github.com/harshgitty58/Flash_Flood_Prediction |
| State described | October 2026 (commit history on `main`) |
| Purpose | One document that explains every dataset, model, metric and output in the project, with sources, so it can be presented and examined as an ML project |

Every number in this guide comes from a file in the repository, named where it is used. Nothing is quoted from memory.

---

## Contents

1. The problem in one page
2. System overview
3. Study area and spatial units
4. Datasets: every source in the project
5. Data volumes, coverage and the study windows
6. Ground truth: flood labels
7. Data cleaning and quality control
8. Feature engineering: all features with formulas
9. Target variable and the splits
10. Models: what was trained and how
11. Hyper-parameter tuning
12. Evaluation protocols
13. Results: accuracy at every level
14. Multi-source fusion ablation (which data helps)
15. Uncertainty: calibration and conformal prediction
16. Explainability (SHAP)
17. Robustness to sensor failure
18. From probabilities to warnings: the hybrid tiers
19. Impact and exposure layer
20. Experiments tested and not adopted
21. v1.0 research studies (`results/v3/`)
22. How the outputs look (API and web console)
23. Engineering quality: latency, tests, reproducibility
24. Comparison with real systems and published work
25. Limitations and how they are handled
26. What comes next
27. Glossary and formulas
28. Source and licence list

---

## 1. The problem in one page

**The hazard.** Uttarakhand is a Himalayan state with steep valleys, intense monsoon rain and settlements packed along rivers. Recent disasters:
- Kedarnath 2013;
- Chamoli 2021, a rock-ice avalanche;
- many cloudburst floods every monsoon (for example Dharali, 5 Aug 2025).

Flash floods give minutes to hours of warning.

**The question.** For every rain gauge and district: *will a flood be recorded in the next 24 hours, how sure are we, why, and what is exposed?*

**What makes it hard (and what this project is honest about):**
- **Rare events.** In the labelled data only 4–8 % of station-hours are flood hours.
- **Few labels.** About 50 official flood district-days fall in the training window.
- **Gauges miss cloudbursts.** Half of the documented floods had less than 50 mm of rain in 24 h at the district's wettest gauge (`results/model_upgrade.md`).
- **Labels are district-days, not points.** A recorded flood marks the whole district.

**The answer the project gives:** a calibrated XGBoost model combined with official IMD rainfall rules into five warning tiers. Every prediction carries:
- a conformal confidence statement;
- SHAP explanations;
- a building-level exposure map based on official river-setback zones.

Evaluation follows the WMO forecast-verification style, with confidence intervals, baselines and external validation.

---

## 2. System overview

```
Raw sources ──► Cleaning & QC ──► Hourly feature table ──► Target (flood today/tomorrow)
(rain, river,     (error codes,      (rain sums, API,          │
 floods, slides,   quarantine,        discharge, history,      ▼
 districts, ERA5,  offline gauges)    landslides, terrain)  LR / RF / XGBoost  ──► Venn-Abers calibration
 terrain)                                                      │                       │
                                                               ▼                       ▼
                                             Event cross-validation        Mondrian conformal sets
                                                               │                       │
                                                               └────► Hybrid warning tiers ◄── IMD rainfall rule
                                                                              │
                                    WMO-style verification ◄──────────────────┤
                                                                              ▼
                                       Building exposure (setback zones) ──► JSON export ──► FastAPI + React console
```

The whole chain is one command, `python scripts/run_all.py` (28 stages). It ends with a lineage audit (`scripts/audit_pipeline.py`) that checks every stage exists, is newer than its inputs, and agrees with the previous stage.

---

## 3. Study area and spatial units

| Item | Value |
|---|---|
| Region | Uttarakhand, India |
| Bounding box | lat 28.5–31.5 °N, lon 77.5–81.1 °E (`params.yaml`, `src/config.py`) |
| Districts (13) | Almora, Bageshwar, Chamoli, Champawat, Dehradun, Haridwar, Nainital, Pauri Garhwal, Pithoragarh, Rudraprayag, Tehri Garhwal, Udham Singh Nagar, Uttarkashi |
| Divisions | Garhwal (7 districts), Kumaon (6 districts) |
| Time zone | stored and displayed as IST (Asia/Kolkata); gridded sources are UTC |
| Units of analysis | station-hour (the model) and district-day (how warnings are issued and judged) |

---

## 4. Datasets: every source in the project

### 4.1 Sources used by the deployed model

| # | Dataset | Provider | Type | Resolution | Coverage | Size in project | Used for |
|---|---|---|---|---|---|---|---|
| 1 | Telemetry hourly rainfall | Central Water Commission (CWC), via India-WRIS | gauge time series | hourly, **44 usable gauges** (47 raw) | 2022-01 → 2026-09 | 46,379 raw rows | rainfall features (10) |
| 2 | River discharge | CWC | gauge time series | 15 min → hourly, **7 gauges** | 2023-06 → 2025-12 | 364,868 raw / 90,303 hourly rows | discharge features (4) |
| 3 | Flood event inventory | IMD (curated) | event list | district, start date | 1970 → 2023-08-26 | **121 events** | training labels (v1), flood-history features |
| 4 | District Flood Severity Index, flooded area %, fatalities, flood duration, population | curated district tables | static per district | 13 districts | — | 13 rows each | static history features (5) |
| 5 | Landslide inventory | Geological Survey of India (Bhukosh) | points | point | historical | **5,443 points** | landslide features (4) |

### 4.2 Sources used for labels, validation and research

| # | Dataset | Provider | Type | Coverage | Used for |
|---|---|---|---|---|---|
| 6 | SANDRP cloudburst compilations | South Asia Network on Dams, Rivers & People | web reports | monsoons 2022, 2023 | label audit, labels v2, external validation |
| 7 | Sphere India situation reports | Sphere India | reports | 2022–2025 | labels v2, external validation |
| 8 | MHA / NDMI daily flood situation reports | Ministry of Home Affairs (NERC) | PDFs (OCR where scanned) | 2022–2025 | labels, district loss tables |
| 9 | EM-DAT | CRED, UCLouvain | disaster database | 2023–2025 (India) | labels (derived district-days only) |
| 10 | Curated news list | public news | event list | 2024–2025 | external validation |
| 11 | USDMA hydromet reports | Uttarakhand State Disaster Management Authority | twice-daily station reports | 2022 → | district-day model, threshold study |
| 12 | ERA5 / ERA5-Land (via Open-Meteo) | ECMWF / Copernicus C3S | reanalysis at the gauge cell | 2022 → | reanalysis rain, soil moisture 0–7 and 7–28 cm (Exp H) |
| 13 | AWS Terrain Tiles (Terrarium) | AWS open data (SRTM-based) | DEM tiles, zoom 12 (~38 m) and 13 (~19 m) | static | terrain at gauges (Exp H), impact-layer height above river |
| 14 | Copernicus DEM GLO-30 | ESA / Airbus via AWS open data | 30 m DEM | static | 30 m terrain at all 51 gauges (`results/v3/terrain_at_gauges.csv`) |

### 4.3 Sources used by the impact layer

| # | Dataset | Provider | Used for |
|---|---|---|---|
| 15 | Global ML Building Footprints | Microsoft (polygons extracted from imagery by a deep segmentation model) | buildings: 575,339 scored |
| 16 | OpenStreetMap | OSM contributors (Overpass API) | rivers/streams, roads, bridges, schools, hospitals, places |
| 17 | GeoNames | GeoNames | town and village names |

### 4.4 Sources being added for v1.0 (downloaded, not yet in a model)

| # | Dataset | Provider | Status (Oct 2026) |
|---|---|---|---|
| 18 | GPM IMERG V07 Final, daily, 0.1° | NASA GES DISC | **downloaded**: 9,039 days 2001–2025 (Uttarakhand box only) |
| 19 | ERA5 hourly single levels (CAPE, total column water vapour, temperature, dewpoint, pressure, wind, convective rain) | Copernicus CDS | downloading (queued requests) |
| 20 | ERA5-Land daily (soil water layers 1–4, runoff, snow water equivalent, snowmelt) | Copernicus CDS | downloading |
| 21 | GloFAS v5 river discharge (daily mean) | Copernicus EWDS | queued |

Download scripts: `scripts/fetch_imerg_daily.py`, `scripts/fetch_cds.py`.

---

## 5. Data volumes, coverage and the study windows

### 5.1 The final hourly table
Source: `web/public/data/model.json`

| Quantity | Value |
|---|---|
| Station-hours | **518,304** |
| Rain gauges | 44 (plus 7 river gauges) |
| Districts | 13 |
| Time span | 2022-01-31 → 2026-09-14 |
| Labelled station-hours | **126,904** |
| Positive (flood) hours | **1,951** |
| Label end | 2023-08-26 (end of the IMD inventory) |

### 5.2 Where the sources overlap
Source: `results/data_windows.json`

| Window | Dates | Sources | Use |
|---|---|---|---|
| A: training window | 2022-02-01 → 2023-08-25 | rainfall + labels (+ discharge where present) | train / validate / test |
| B: all sources | 2023-06-07 → 2023-08-25 | rainfall + discharge + labels | reported only (too short) |
| C: sensor overlap | 2023-06-07 → 2025-12-31 | rainfall + discharge | replay now; training once labels are completed |
| Replay | 2023-08-26 → | everything except labels | inference only (the web app's "replay") |

**Why labels end in 2023.** After the IMD inventory stops, "no record" no longer means "no flood". Those hours are therefore *unlabelled*, not negative. This rule prevents the model from learning that 2024–26 had no floods.

---

## 6. Ground truth: flood labels

### 6.1 Training labels (v1)
- **Source:** the IMD flood inventory.
- **Target:** a flood recorded in the gauge's district *on day D or D+1*.
- **The district-name bug.** IMD spells some districts differently ("Rudra Prayag", "Udam Singh Nagar", "Garhwal"). Before the fix, **13 of 29 flood days (45 %) were silently dropped**.
- **Effect of the fix:** test ROC-AUC rose from 0.53 to **0.71**, and PR-AUC from 0.04 to **0.15**.

### 6.2 The multi-source event list (2022–2025)
Built by `scripts/build_labels.py`; summary in `data/external/labels/labels_summary.json`.

| Quantity | Value |
|---|---|
| Events | **96** |
| District-days | **130** |
| By year | 2022: 28 · 2023: 40 · 2024: 11 · 2025: 17 |
| By date confidence | high 88 · medium 2 · low 6 |
| By source family | SANDRP 52 · Sphere 44 · IMD 29 · EM-DAT 25 · curated 14 |
| Corroborated by ≥ 2 sources | 22 |

Each event records:
- date and end date;
- district and place;
- type;
- deaths and missing;
- severity;
- date confidence;
- sources and URLs.

### 6.3 Label audit
Source: `src/label_audit.py`

- SANDRP documents **40 damaging events that IMD misses** (against 26 IMD events) in the overlapping period.
- So official labels under-count hill cloudbursts.
- This is the main reason the absolute scores are modest: the model is graded against an incomplete answer key.

### 6.4 How labels are used
- **2022 – Aug 2023 (IMD):** training, validation and test.
- **Sep 2023 – 2025 (multi-source list):** **external validation only**, never training, because the lists cover major reported disasters, not every flood.

---

## 7. Data cleaning and quality control

Code: `src/cleaning.py`. Constants in `params.yaml → qc`.

### 7.1 Rules

| Rule | Value | Action |
|---|---|---|
| Telemetry error code | 511.5 mm | removed (NaN) |
| Negative values | < 0 | removed |
| Plausibility cap | > 150 mm/h | removed (same cap enforced on API input) |
| Faulty-gauge quarantine | > 20 % of a gauge's readings above 100 mm/h | whole gauge removed (e.g. Yamuna Colony, median 272 mm/h; Roorkee_2; Purola_1) |
| Discharge cap | > 15,000 m³/s | removed |
| Offline gauge | no record for 7 days (Jun–Sep) or 45 days (other months) | those hours dropped (a dead gauge is never treated as dry) |
| Timestamps | hours 0–9 without a leading zero | parsed correctly (the original bug lost **47 %** of rows) |
| Duplicates | (station, hour) | removed; tested |

### 7.2 Result on rainfall
40,640 rows were checked:
- **33,377 valid**
- 5,960 from quarantined gauges
- 794 error codes
- 443 implausible
- 66 negative

### 7.3 Five silent bugs found by testing the data
All five are now guarded by tests.
1. **Timestamps:** hours 0–9 had no leading zero and were silently dropped, losing 47 % of rainfall rows.
2. **Offline vs dry:** long outages were filled as 0 mm, so 58 % of the hourly grid was fake dry weather.
3. **Label timing:** the target marked the day *before* each flood.
4. **A faulty gauge** (median 272 mm/h) produced fake EXTREME alerts.
5. **District-name mismatch** in the label join dropped 45 % of flood days.

### 7.4 Raw-data integrity
`curated_dataset/MANIFEST.sha256` pins all 11 raw files. Hashes are taken over line-ending-normalised bytes, so Windows and Linux agree. A test and the audit both check them.

---

## 8. Feature engineering: all features with formulas

Every feature uses only information available **before** time t. A truncation test checks this: deleting all data after t must not change the value at t.

### 8.1 Rainfall (10 features in the deployed model)

| Feature | Definition |
|---|---|
| `rain_1h` | rain in the hour (t−1, t] |
| `rain_3h`, `rain_6h`, `rain_12h`, `rain_24h`, `rain_48h`, `rain_72h` | rolling sums over clock hours |
| `rain_max_intensity_24h` | maximum hourly rain in the last 24 h |
| `rain_intensity_change_1h` | r(t) − r(t−1) |
| `api_decay_85` | Antecedent Precipitation Index, API(t) = 0.85·API(t−1) + P(t) (hourly; half-life 4.3 h) |

### 8.2 River discharge (4)
`discharge_clean`, `discharge_change_1h`, `discharge_change_3h`, `discharge_anomaly` (value minus the station-month median).

### 8.3 Flood history (5 static, district level)
`district_flood_severity_index`, `district_flooded_area_pct`, `district_historical_fatalities`, `district_population`, `district_mean_flood_duration_days`.

### 8.4 Landslides (4)
- `dist_to_nearest_landslide_km`
- `landslide_count_5km`, `landslide_count_10km`
- `is_landslide_hotspot`

### 8.5 Research features (built and tested in Exp H; not in the deployed model)
- **ERA5 rain:** 1, 3, 6, 24, 72 h sums and the max 1 h in 24 h.
- **Soil moisture:** 0–7 cm, 7–28 cm, and the anomaly.
- **Station-relative rainfall:** the percentile of 24 h and 72 h rain at that station; the seasonal z-score.
- **Source agreement:** the log ratio of gauge to ERA5 rain; both wet (gauge ≥ 35.5 mm and ERA5 ≥ 15 mm).
- **Terrain at the gauge:** elevation, slope, 2 km relief, 1 km topographic position index.
- **Calendar:** hour, day of week, month, monsoon flag. Tested; excluded from the final model.
- **Latitude and longitude:** excluded after they were found to carry 38 % of importance (location memorisation).

### 8.6 Terrain from the 30 m Copernicus DEM (`src/terrain.py`, v1.0)
Computed at all 51 gauges, in `results/v3/terrain_at_gauges.csv`:

| Quantity | How it's computed |
|---|---|
| elevation, slope | Horn method |
| aspect | — |
| terrain ruggedness | TRI |
| topographic wetness | TWI = ln(a/tanβ) |
| stream power | SPI = ln(a·tanβ) |
| upstream area | Priority-Flood D8 routing |
| height above nearest drainage | HAND, along the flow path |
| distance to channel, 1 km relief | — |

Checked against the earlier DEM: elevation correlation r = 1.000, median difference 4 m.

### 8.7 Normalisation
`src/normalization.py`, fitted on the training window only:
- **log_robust** for heavy-tailed positives (rain, API, discharge, counts);
- **signed_log** for changes and anomalies;
- **z-score** for indices and distances.

The parameters are exported to `results/preprocessing/normalization_params.json` and reused at inference.

### 8.8 Online features (for live use)
`src/online_features.py` updates every rolling feature in **O(1) per new hour**:
- a 72-hour ring buffer with running sums;
- a monotonic deque for the 24 h maximum;
- the API recursion.

A test proves it gives the same values as the batch pipeline.

---

## 9. Target variable and the splits

**Target:** `flood_event_24h` = 1 if a flood is recorded in the station's district on that calendar day or the next one; otherwise 0. It is NaN (unlabelled) after 2023-08-26.

**Chronological splits** (`results/splits.json`). Labelled rows only; no random shuffling, so no future data leaks into the past.

| Split | Dates | Rows | Flood hours | Base rate | Stations |
|---|---|---|---|---|---|
| Train | 2022-06-21 → 2023-06-30 | 94,154 | 367 | 0.4 % | 37 |
| Validation | July 2023 | 20,280 | 864 | 4.3 % | 35 |
| Test (held out) | 1–25 Aug 2023 | 12,469 | 720 | 5.8 % | 29 |

**Training type:**
- **supervised binary classification** on tabular time-series features;
- **heavily imbalanced** (class weights; no resampling);
- **chronological hold-out**, plus **leave-one-event-out cross-validation** (section 12).

---

## 10. Models: what was trained and how

The brief's model ladder:

| Rung | Model | Role | Library |
|---|---|---|---|
| 1 | Logistic Regression | interpretable baseline | scikit-learn 1.7 |
| 2 | Random Forest | non-linear baseline | scikit-learn |
| 3 | **XGBoost** | main model (deployed) | XGBoost 3.2 |
| 4 | XGBoost + conformal prediction | uncertainty (main research component) | own implementation (`src/conformal.py`) |
| 5 | SHAP on the best model | explanations | SHAP 0.51 |

Extra models built for experiments:
- an equal-weight ensemble (LR + RF + XGB);
- a district-day logistic model (L2, C = 0.1);
- a pooled district-day model with district intercepts.

**The deployed model:** XGBoost, feature set **Exp G "Static history"**, **23 features**:
- 10 rainfall;
- 4 discharge;
- 5 district history;
- 4 landslide.

Lat/lon and the drifting history counters are excluded. Preprocessing is median imputation, then the parameterised normaliser. The pipeline is saved at `models/xgboost/model.joblib`.

**Selected hyper-parameters** (`results/hyperparameter_tuning/*_best_params.json`):

| Model | Hyper-parameters | Operating threshold (raw score, max-F1 on validation) |
|---|---|---|
| Logistic Regression | liblinear, L2, C = 0.01, class_weight = balanced | 0.85 |
| Random Forest | 200 trees, max_depth 5, min_samples_leaf 1, balanced_subsample | 0.45 |
| XGBoost | 100 trees, max_depth 5, learning_rate 0.01, subsample 0.8, colsample 1.0, scale_pos_weight 255.55 | 0.25 |

---

## 11. Hyper-parameter tuning

- **Method:** randomised / grid search with **TimeSeriesSplit** on the training data only (`src/tune_models.py`), so validation and test are never used for tuning.
- **XGBoost search space:**
  - n_estimators {100, 200}
  - max_depth {3, 5, 7}
  - learning_rate {0.01, 0.05, 0.1}
  - subsample {0.8, 1.0}
  - colsample_bytree {0.8, 1.0}
  - scale_pos_weight {1, neg/pos}
- **Threshold freezing:** each model's operating threshold is chosen once on validation (max F1), then applied unchanged to test.
- **Reproducibility:** seed 42 everywhere. The model registry (`results/model_registry.csv`) lists the current models with validation *and* test metrics, with the earlier runs in a legacy log.
- **v1.0 rule:** the model-selection rule was written before any new tuning (`docs/adr/ADR-007-model-selection.md`).

---

## 12. Evaluation protocols

| Protocol | What it does | Why |
|---|---|---|
| **Chronological hold-out** | train → July 2023 validation → August 2023 test | standard temporal generalisation |
| **Leave-one-event-out CV** (`src/event_cv.py`) | each of 6 flood episodes is held out in turn; test = rows within ±3 days; train = rows more than 7 days away | with ~7 episodes, a single split is too fragile |
| **District-day verification** (`src/verification.py`) | one warning per district per day, judged WMO-style with block-bootstrap 95 % CIs over days (1,000 resamples) | how warnings are actually issued |
| **External validation** (`src/external_validation.py`) | 29 documented events after Sep 2023, never seen in training | independent check of detection |
| **Baselines** | climatology, persistence, district prior, IMD rain rule | the model must beat what a forecaster already has |

**Metric definitions:** `docs/metrics.md`.
- **PR-AUC is always read against the base rate.** Lift = PR-AUC ÷ base rate.
- **The headline district-day CSI uses the strict definition:** a flood *starting* on day D, with the warning taken as the highest tier over D−1..D.

---

## 13. Results: accuracy at every level

### 13.1 Hour level at the frozen thresholds
Source: `results/metrics/metrics_summary.csv`

| Model | Split | Precision | Recall | F1 | Specificity | MCC | ROC-AUC | PR-AUC | Brier | False alarms / station-month |
|---|---|---|---|---|---|---|---|---|---|---|
| Logistic Regression | validation | 0.124 | 0.219 | 0.158 | 0.931 | 0.115 | 0.642 | 0.076 | 0.143 | 38.1 |
| Logistic Regression | test | 0.169 | 0.211 | 0.188 | 0.937 | 0.133 | 0.741 | 0.139 | 0.123 | 25.7 |
| Random Forest | validation | 0.150 | 0.358 | 0.212 | 0.910 | 0.179 | 0.632 | 0.113 | 0.078 | 50.0 |
| Random Forest | test | 0.173 | 0.369 | 0.236 | 0.892 | 0.185 | **0.788** | **0.152** | 0.096 | 43.8 |
| **XGBoost (deployed)** | validation | 0.139 | 0.366 | 0.201 | 0.899 | 0.170 | **0.719** | 0.109 | 0.086 | 56.0 |
| **XGBoost (deployed)** | test | **0.222** | **0.574** | **0.320** | 0.877 | **0.295** | 0.708 | 0.150 | 0.093 | 49.8 |

**Reading the table:**
- **Base rate and lift:** the test base rate is 5.8 %, so XGBoost's PR-AUC of 0.150 is **2.6× chance**.
- **Why XGBoost is deployed:** it has the best F1, recall and MCC on test, and the best validation ROC-AUC.
- **Random Forest** ranks slightly better on test (ROC 0.788). The ensemble experiment (section 20) tested combining them.

### 13.2 Event level
**Leave-one-event-out, deployed Exp G** (`results/event_cv/event_cv_summary.csv`):
- pooled **ROC-AUC 0.701**, **PR-AUC 0.186**;
- base rate 0.081, 6 folds, 15,473 rows, 1,248 positives.

**Event detection** (`results/event_cv/event_lead_summary.json`):
- 8 of 19 held-out district floods detected at a 5 % hourly false-alarm rate.
- This is an older definition; the honest lead time in section 13.4 replaces it.

### 13.3 Warning level: district-day, strict WMO definition
Source: `results/verification/verification.json`, hybrid ≥ ALERT

| Split | Layer | POD | FAR | CSI [95 % CI] |
|---|---|---|---|---|
| Test (Aug 2023, 10 events) | **hybrid (deployed)** | **0.70** | 0.90 | **0.095** [0.034–0.165] |
| Test | ML only | 0.50 | 0.90 | 0.091 |
| Test | rainfall rule only | 0.30 | 0.90 | 0.083 |
| Test | district prior only | 1.00 | 0.96 | 0.036 |
| Test | persistence (flood yesterday) | 0.10 | 0.90 | 0.053 |
| Validation (Jul 2023, 8 events) | hybrid | 0.63 | 0.97 | 0.027 |
| Both months (18 events) | hybrid | 0.67 | 0.95 | 0.046 |

On the test month the hybrid's CSI is **2.6× the district-prior baseline** and **1.8× persistence**.

A *lenient* definition (the training target: flood on D or D+1) gives **CSI 0.169**, with POD 0.63 and FAR 0.81. Quote it only with that label.

### 13.4 Probabilistic skill and lead time
- **Brier skill score vs monthly climatology: 0.073.** Expected calibration error **0.012**, so the probabilities are well calibrated.
- **Honest lead time:** **6 of 18** floods were warned before the event day, **median 3.5 h**. Another 7 had the alert already on as a district baseline, and 5 were missed.

### 13.5 External validation
29 documented events from 2023-09-15 to 2025-09-17; 21 had a gauge reporting in the district.

| Layer | Detected at ≥ ALERT | POD [95 % CI] |
|---|---|---|
| **Hybrid (deployed)** | **7 / 21** | **0.33** [0.14–0.52] |
| Rainfall rule only | 6 / 21 | 0.29 |
| ML only | 3 / 21 | 0.14 |

Detected events include:
- the Kedarnath trek route (31 Jul 2024);
- Haridwar (31 Jul 2024);
- Champawat, Chamoli and Pauri (8 Jul 2024);
- the Yamunotri highway (29 Jun 2025);
- **Dharali (5 Aug 2025)**.

### 13.6 District ranking ("Districts to watch")
- **On the test month:** the share of flood days whose district is among the day's top 3 is **0.455**, against a prior of 0.409.
- **On external events:** **0.345**, against a prior of 0.207 and chance of 0.231.

---

## 14. Multi-source fusion ablation (which data helps)

Leave-one-event-out XGBoost; pooled values. Source: `results/event_cv/event_cv_summary.csv`

| Experiment | Features | ROC-AUC | PR-AUC | Mean fold ROC | Min fold ROC |
|---|---|---|---|---|---|
| A: rainfall only | 10 | 0.497 | 0.093 | 0.521 | 0.347 |
| B: + river discharge | 14 | 0.548 | 0.101 | 0.626 | 0.451 |
| C: + flood history | 21 | **0.772** | 0.223 | 0.797 | 0.629 |
| D: + landslide / terrain | 25 | 0.772 | **0.236** | 0.758 | 0.568 |
| E: + season and lat/lon | 32 | 0.655 | 0.141 | 0.662 | 0.500 |
| F: full minus lat/lon | 30 | 0.614 | 0.126 | 0.649 | 0.379 |
| **G: static history (deployed)** | **23** | 0.701 | 0.186 | 0.770 | 0.580 |
| H: + ERA5, soil, terrain | 42 | 0.703 | 0.147 | 0.724 | 0.585 |
| T: trigger only | 29 | 0.602 | 0.104 | 0.565 | 0.473 |

**What it shows:**
- **Rain at the gauge alone is no better than chance (0.50).** Gauges miss local cloudbursts.
- **Flood history adds the most.** The model learns *where* floods happen.
- **G replaced C and D in deployment.** C and D used history counters that keep growing after the labels end, which would make the model extrapolate in replay. G uses only static history.

**Feature importance** (share of mean |SHAP|):

| Group | Share |
|---|---|
| Flood history | 66 % |
| Rainfall | 24 % |
| Landslide | 10 % |
| Discharge | 0 % (only 7 gauges, mostly absent in training) |

---

## 15. Uncertainty: calibration and conformal prediction

Code: `src/conformal.py`

### 15.1 Calibration: inductive Venn-Abers
1. For each score s, isotonic regression is fitted twice: once with (s, 0) and once with (s, 1) added to the calibration set. That gives a probability interval [p0, p1].
2. The calibrated probability is p = p1 / (1 − p0 + p1).
3. The calibration set is July 2023: 20,280 hours, 864 floods.
4. For speed, the result is served as a **400-point look-up grid**.

**Effect on test:** Brier score improves from 0.093 (raw) to **0.052** (calibrated).

### 15.2 Mondrian (class-conditional) conformal prediction
- p-values are computed separately for each class.
- The prediction set at level 1−α is every class whose p-value exceeds α: {FLOOD}, {NO FLOOD}, or both = **UNCERTAIN**.

| Nominal level | Coverage (all) | Coverage (flood hours) | Coverage (no-flood) | Uncertain share |
|---|---|---|---|---|
| 80 % | 0.884 | **1.00** | 0.877 | 0.85 |
| 90 % | 0.884 | **1.00** | 0.877 | 0.85 |
| 95 % | 0.973 | **1.00** | 0.971 | 0.97 |

**What it means:**
- **Every real flood hour** fell inside the 90 % set.
- The model often answers "uncertain", which is the honest answer with gauge-only inputs.
- **Known limit:** the 80 % and 90 % sets coincide because the model emits few distinct scores (section 21).

### 15.3 In the product
Each prediction shows:
- the calibrated probability;
- a confidence value (1 − the second-largest p-value);
- credibility;
- the 90 % set.

---

## 16. Explainability (SHAP)

Code: `src/explain.py`. TreeSHAP on the deployed XGBoost.

### 16.1 Global importance
Mean |SHAP| in log-odds units, from `results/shap/shap_global_importance.csv`:

| Rank | Feature | Mean \|SHAP\| |
|---|---|---|
| 1 | district_flood_severity_index | 1.101 |
| 2 | rain_48h | 0.181 |
| 3 | rain_72h | 0.114 |
| 4 | landslide_count_10km | 0.104 |
| 5 | dist_to_nearest_landslide_km | 0.055 |
| 6 | rain_max_intensity_24h | 0.043 |
| 7 | rain_24h | 0.033 |
| 8 | api_decay_85 | 0.025 |

### 16.2 Local explanations and checks
- **Top 3 drivers per prediction:** every prediction's top-3 signed drivers appear in the station drawer of the web app.
- **By district:** mean SHAP for each district is in `shap_mean_by_district.csv`.
- **Tested:** SHAP values plus the base value equal the model's margin, within 10⁻³ (`tests/test_model_behaviour.py`).

---

## 17. Robustness to sensor failure

Code: `src/robustness.py`. Inference-time degradation only (no retraining), on the validation and test rows. A missing input becomes NaN and is filled by the training median, exactly what happens when a sensor drops out live.

| Scenario | ROC-AUC | Drop |
|---|---|---|
| Baseline (all inputs) | 0.716 | — |
| Rainfall noise, 5 % of std | 0.714 | 0.002 |
| Rainfall noise, 20 % of std | 0.712 | 0.004 |
| Rainfall noise, 50 % of std | 0.705 | 0.010 |
| River discharge offline | 0.716 | 0.000 |
| Rainfall gauge offline | 0.711 | 0.005 |
| **Flood-history records unavailable** | **0.500** | **0.216** |
| Landslide inventory unavailable | 0.714 | 0.001 |
| Random dropout, 10 % of inputs | 0.687 | 0.028 |
| Random dropout, 25 % of inputs | 0.647 | 0.069 |
| Random dropout, 50 % of inputs | 0.593 | 0.122 |
| Noisy rain + discharge offline | 0.713 | 0.003 |

**Reading:**
- The model is robust to noisy or missing gauges.
- It depends heavily on the district-history inputs. This is the "prior dominance" that the v1.0 plan addresses.

---

## 18. From probabilities to warnings: the hybrid tiers

Code: `src/warning_levels.py`. Values in `params.yaml`.

**Five tiers:** NORMAL, WATCH, ALERT, SEVERE, EXTREME. They map to IMD's colour practice: Green, Yellow, Orange, Red, Red + "extreme".

**ML layer.** The calibrated probability is compared with 2× / 5× / 10× / 20× the calibration base rate (0.0426):

| Tier | Cut-off |
|---|---|
| WATCH | 0.085 |
| ALERT | 0.213 |
| SEVERE | 0.426 |
| EXTREME | 0.852 |

A conformal FLOOD-only set at 90 % lifts the tier to at least ALERT.

**Rainfall layer (official IMD 24 h categories):**

| IMD category | 24 h rain | Tier |
|---|---|---|
| moderate | 15.6 mm | WATCH |
| heavy | 64.5 mm | ALERT |
| very heavy | 115.6 mm | SEVERE |
| extremely heavy | 204.5 mm, or a **cloudburst** (≥ 100 mm in 1 h) | EXTREME |

The rain tier moves up one level in landslide-hotspot, flood-prone districts, and down one level in safe districts.

**Final tier** = max(ML tier, rain tier). The layer that set it is stored as the `trigger`.

**Example from the live replay (12 Sep 2024, 19:00):**
- Haldwani shows **EXTREME**: 141 mm in 24 h ("very heavy") plus the flood-prone uplift.
- The ML probability there is only 2 %. The interface shows both, so the user knows the rainfall rule raised the alert.

**Station-hour performance on test (≥ ALERT):**

| Layer | Precision | Recall |
|---|---|---|
| Hybrid | 0.234 | **0.650** |
| ML alone | 0.222 | 0.574 |
| Rain alone | 0.380 | 0.083 |

---

## 19. Impact and exposure layer

Code: `scripts/build_impact_layer.py`; checked by `scripts/audit_impact.py`.

### 19.1 Zones and classes
Buildings within **5 km** of each hazard centre are classed by **official river-setback zones**:

| Zone | Distance from river | Legal basis | Building class |
|---|---|---|---|
| A | ≤ 50 m | NGT order, Dec 2017: no construction | = hazard tier |
| B | 50–100 m | NGT regulatory zone; Jal Shakti Flood Plain Zoning guidelines 2025 | one level lower |
| C | 100–200 m | Uttarakhand High Court, Aug 2013 | two levels lower |
| — | beyond 200 m | — | MINIMAL |

### 19.2 Results (replay, 12 Sep 2024, 19:00)

| Quantity | Value |
|---|---|
| Buildings scored (all centres) | **575,339**, with **0** zone or class mismatches in the audit |
| Around the 27 reporting gauges | 261,030 buildings: CRITICAL 2,149 · HIGH 2,806 · MODERATE 5,342 · LOW 5,523 · MINIMAL 245,210 |
| Roads | 1,327 segments |
| Bridges | 228 |
| Named places and landmarks | 13,752 |

### 19.3 Coverage gaps
- **Offline gauge:** its last report within 7 days is used.
- **No gauge within 5 km:** the district estimate is used, from the district-day ranking.

### 19.4 Height above river
Shown for information only. The legal flood plain is the 1-in-100-year highest flood level + 1 m (Uttarakhand Flood Plain Zoning Act 2012), and those maps are not public. The layer is therefore labelled an **exposure proxy, not inundation**.

### 19.5 Logic check of current alerts
- **Correct:** Haldwani EXTREME and Pithoragarh SEVERE (heavy and very heavy rain).
- **Flagged for v1.0:**
  - three ML-only ALERTs on near-dry days (Chakrata, Joshiyara, Sonprayag);
  - the district ranking always puts 3 districts at ALERT (Dehradun, Rishikesh on a dry day);
  - lake-side exposure (Nainital) isn't measured, because zones use river distance only.

---

## 20. Experiments tested and not adopted

Each experiment's adoption rule was written before it ran (`MODEL_UPGRADE_PLAN.md`, `results/model_upgrade.md`).

| Experiment | Result | Decision |
|---|---|---|
| **E1: equal-weight ensemble** (LR + RF + XGB, percentile-averaged) | test ROC 0.708 → 0.784; event-CV PR-AUC 0.188 → 0.205; district-day CSI unchanged or lower | not adopted (ranking improves, warnings don't) |
| **E2: rainfall thresholds fitted on 46 events** (hills 24 h: ALERT 12.0 / SEVERE 42.4 / EXTREME 108.3 mm) | catches more 2025 events (5/10 vs 2/10) but doubles alerts and halves CSI (0.169 → 0.088) | not adopted |
| **E3: pooled district-day model** | test ROC 0.753, PR-AUC 0.155 (base 0.068); CSI 0.105 vs hybrid 0.169 | alert layer not adopted; **ranking view adopted** ("Districts to watch") |
| **Label v2** (IMD + SANDRP + situation reports) | event-CV ROC 0.70 → 0.78, but test PR-AUC 0.150 → 0.113 | not adopted as training labels; kept as an answer key (XGBoost CSI 0.15 → 0.20 against it) |
| **Tuned rainfall rule** (32 candidates) | best candidate didn't beat the deployed rule by its CI | not adopted |

**Conclusion recorded in the project:** the limit is the labels and the gauges' blindness to local cloudbursts, not the model class.

---

## 21. v1.0 research studies (`results/v3/`)

| Study | Question | Finding |
|---|---|---|
| **RQ4: calibration** (`src/calibration_study.py`) | which calibrator is best? | **Platt and beta calibration pass the pre-set rule:** test log-loss 0.199 vs 0.203, ECE 0.013 vs 0.031, 109 distinct probabilities vs 22. **Root cause of the coarse probabilities:** the model emits only 109 distinct raw scores, and 72 % of test hours share one. |
| **RQ8: hysteresis** (`src/hysteresis_study.py`) | do warnings flicker? | No: the tiers change only **0.41 times per gauge-day**. Hysteresis isn't needed. |
| **V-38: monotone constraints** (`src/monotone_study.py`) | does more rain ever lower risk? | Yes, in **3.2 %** of hours (worst −0.29). Constraints remove every case but cost 0.015 test PR-AUC, so they're not adopted yet. |
| **Terrain at gauges** (`scripts/terrain_at_gauges.py`) | the brief's terrain parameters | computed for all 51 gauges from the 30 m DEM; ready for v1.0 |

---

## 22. How the outputs look (API and web console)

### 22.1 Output of one prediction
From `POST /predict`. Illustrative shape (field names are real):

```json
{
  "station": "Haldwani_1",
  "time": "2024-09-12T19:00:00",
  "p_calibrated": 0.0182,
  "confidence": 0.67, "credibility": 0.63,
  "cp_set_90": "UNCERTAIN",
  "tier": "EXTREME", "tier_ml": "NORMAL", "tier_rain": "EXTREME", "trigger": "rainfall",
  "rain_24h": 140.5,
  "drivers": [ {"feature": "district_flood_severity_index", "shap": -0.84},
               {"feature": "rain_max_intensity_24h", "shap": -0.61}, ... ],
  "latency_ms": 15.1
}
```

### 22.2 API (FastAPI)
- **Data:** `/health`, `/stations`, `/risk/snapshot`, `/risk/timeline`, `/model/summary`, `/metrics`, `/events`, `/impact/summary`, `/impact/tiles/{z}/{x}/{y}`, `/landmarks`.
- **Prediction:** `POST /predict`, `POST /predict/scenario` (what-if, for example "what if 120 mm falls?").
- **Admin:** `POST /admin/reload`, which needs a token.
- **Behaviour:** responses are cached with ETag/304, and every response carries its own timing header.

### 22.3 Web console (React + MapLibre)

| Page | Shows |
|---|---|
| Landing | live replay card; **Verified results** (CSI 0.095, 7/21 external, BSS 0.073, 6/18 warned) |
| Overview | peak tier and trigger, regional trajectory, global drivers, districts to watch, data-source health |
| Forecast | probability over the replay window; lead-time result |
| Risk Map | satellite / terrain / dark basemaps, 3-D terrain; station drawer with probability, confidence, 90 % set and SHAP drivers |
| Impact | 575k building outlines by class, landmarks, bridges, place search |
| Uncertainty | fusion ablation, conformal coverage, sensor-failure table |
| Events | recorded flood events |
| Data & Model | model comparison, SHAP importance, event-CV table, coverage by month, normalisation |
| Metrics | hour-level table with base rate and lift, threshold slider, confusion matrix, WMO verification with CIs, external validation, label audit |
| System | external services, API status, measured latency |

---

## 23. Engineering quality: latency, tests, reproducibility

### 23.1 Latency
Source: `results/latency/benchmarks.csv`

| Path | Before | After |
|---|---|---|
| Buildings for one map view | 66.5 MB file, 3.0 s p95 | 0.74 MB tile, 175 ms p95 (adaptive quadtree tiles) |
| Features for one station-hour | 1.27 ms (batch) | 0.17 ms (O(1) online) |
| Calibrate one score | 4.32 ms (two isotonic fits) | 0.006 ms (look-up table) |
| `POST /predict` | — | 15 ms p50, **17 ms p95** |
| Snapshot endpoint | — | 1.2 ms p50 (0.6 ms cached) |
| API memory on Linux | — | 335 MB (fits a 512 MB free host) |

### 23.2 Quality gates
- **51 automated tests:**
  - data contracts and raw-file hashes;
  - labels;
  - online/batch feature parity;
  - terrain algorithms;
  - model behaviour;
  - API contract;
  - security.
- **Pipeline audit:** `scripts/audit_pipeline.py` reports **0 fail, 0 warn**.
- **GitHub Actions CI:** runs the tests and the web build on every push.
- **Configuration:** every constant lives in `params.yaml`.
- **Documentation:** `docs/` holds the architecture, metric definitions, licences, decision records and a runbook.

---

## 24. Comparison with real systems and published work

### 24.1 Operational systems this project resembles

| System | What it does | How PRAHAR relates |
|---|---|---|
| **Flash Flood Guidance System (FFGS)**, WMO / Hydrologic Research Center; the South Asia regional implementation covers India | estimates the rain needed to cause bankfull flow per small basin and compares it with observed or forecast rain | PRAHAR's IMD rainfall layer is a simpler, gauge-based guidance rule; experiment E2 tested FFG-style thresholds fitted on events |
| **IMD district rainfall warnings** (Green / Yellow / Orange / Red) | official district warnings from forecasts | PRAHAR's tiers use the same colour logic and IMD's rainfall categories; comparing against archived IMD warnings is planned |
| **CWC flood forecasting** | stage forecasts at major river stations | complements PRAHAR, which targets small, fast catchments where CWC has no forecast station |
| **GloFAS** (Copernicus) | global river-discharge forecasts | being added as an input (GloFAS v5 discharge) |
| **Google Flood Hub** | ML riverine flood forecasting on large rivers | covers large rivers; flash floods in small Himalayan catchments are outside its scope |

### 24.2 Published ML flash-flood studies (the brief's reading list)

| Paper (from the course brief) | Relevance to PRAHAR |
|---|---|
| Uncertainty-aware ML for flash-flood prediction (Trans. GIS, 2025) | same aim: uncertainty under noisy inputs; PRAHAR measures it with conformal coverage and a sensor-failure suite |
| Deep-learning probabilistic flash-flood warnings in mountainous catchments (J. Hydrology, 2025) | stresses antecedent rain; PRAHAR uses the API and 48–72 h sums (2nd and 3rd most important features) |
| Spatio-temporal rainfall + hydrologic uncertainty (J. Hydrology, 2025) | motivates multi-source fusion; PRAHAR's ablation measures each source's contribution |
| ML4FF framework, Brazilian watershed (J. Hydrology, 2025) | systematic model comparison; PRAHAR compares LR / RF / XGB on identical folds |
| Explainable flash-flood model, Qinling Mountains (J. Flood Risk Mgmt) | SHAP-based explanations; PRAHAR ships per-prediction SHAP drivers |
| Cross-region deep-learning streamflow forecasting (The Innovation, 2024) | supports transfer to Himachal Pradesh and Sikkim (planned) |

### 24.3 How to compare fairly
- **Many published flood studies report ROC-AUC above 0.9.** Most of these are susceptibility maps (*where* floods happen, from static terrain, with random point splits), or catchment-scale river forecasts with long gauge records. They're a different task and an easier evaluation.
- **PRAHAR predicts *when*,** at the hour and day level, on a future month it never saw, against an official list that under-counts hill floods. On that harder setting:
  - ranking quality is ROC-AUC 0.71–0.79 (test) and 0.70 (event CV);
  - probabilistic skill is positive (BSS 0.073);
  - warnings beat every baseline (CSI 0.095 vs 0.036–0.083);
  - 33 % of independent post-2023 floods were caught.
- **Our own history shows the gap directly.** Before the label-join fix, positives came from only 5 districts, and event CV reported ROC-AUC **0.86**. With all 13 districts' floods correctly joined, the same evaluation gives about 0.70. Earlier still, latitude/longitude carried 38 % of the importance and were removed. The honest, harder number is the one reported.

---

## 25. Limitations and how they are handled

| Limitation | Effect | How it's handled |
|---|---|---|
| Incomplete official labels (IMD misses ~60 % of SANDRP hill events) | scores are understated; positives are noisy | external validation; label audit; 2001–2025 label back-fill planned |
| Gauges miss local cloudbursts | rainfall-only skill ≈ chance | IMERG satellite rain downloaded; ERA5 CAPE and water vapour being added |
| Short training window (1.5 monsoons) | high variance between months (validation CSI 0.03 vs test 0.10) | confidence intervals everywhere; a district-day model on 25 years of gridded data planned |
| Model leans on district history | "where" more than "when"; robustness drop when history is removed | static history only; monotone and offset variants studied |
| Coarse model scores | quantised probabilities; 80 % and 90 % sets coincide | calibration study; finer model planned |
| Exposure is a proxy | not inundation depth | official zones; labelled on screen |
| Nowcast, no forecast input | lead time median 3.5 h | stated; forecast fields are future work |

**Responsible use:** PRAHAR is decision support, not an official warning. Every page carries the disclaimer, and nothing on it implies evacuation orders or damage estimates.

---

## 26. What comes next

The full plan is `PRAHAR_MASTER_PLAN.md`: 24 workstreams and 240 tasks. The main steps:
1. A **district-day model on 2001–2025** gridded data: IMERG (downloaded), ERA5 / ERA5-Land, GloFAS. That is 25 monsoons instead of 1.5.
2. **2001–2025 labels:** IMD Disastrous Weather Events, India Flood Inventory, EM-DAT, news mining.
3. **New features:** the 30 m terrain suite (done at gauges), soil moisture, runoff, CAPE.
4. **Finer XGBoost** (more trees with early stopping), with Platt / beta calibration.
5. **Fixing the flagged alert logic:** no ML alert without rain; district estimates by probability, not rank; lake-side exposure.
6. **Spatial generalisation:** Garhwal ↔ Kumaon, then Himachal Pradesh and Sikkim.

---

## 27. Glossary and formulas

| Term | Meaning |
|---|---|
| POD | hits ÷ (hits + misses): the share of floods warned |
| FAR | false alarms ÷ all warnings |
| CSI | hits ÷ (hits + misses + false alarms) |
| ETS, HSS | skill scores that correct CSI for chance hits |
| ROC-AUC | the probability that a random flood hour scores higher than a random dry hour (0.5 = chance) |
| PR-AUC | average precision; compare it with the base rate (lift = PR-AUC ÷ base rate) |
| Brier score | mean squared error of probabilities; BSS = 1 − Brier ÷ Brier of climatology |
| ECE | mean gap between predicted probability and observed frequency, over 10 bins |
| Venn-Abers | calibration with a validity guarantee, giving a probability interval |
| Conformal set | the set of labels not rejected at level α; coverage is guaranteed under exchangeability |
| SHAP | an additive attribution of a prediction to its features |
| API (rainfall) | Antecedent Precipitation Index: decaying sum of past rain |
| TWI, SPI, HAND | wetness index, stream power index, height above nearest drainage |
| Setback zone | the legal distance band from a river where construction is restricted |

---

## 28. Source and licence list

The full register is in `docs/licences.md`.
- **CWC / India-WRIS:** rainfall, discharge.
- **IMD:** flood inventory, rainfall categories.
- **GSI Bhukosh:** landslides.
- **USDMA:** hydromet reports.
- **Labels:** SANDRP, Sphere India, MHA NDMI, EM-DAT (CRED).
- **NASA GES DISC:** GPM IMERG V07, doi:10.5067/GPM/IMERGDF/DAY/07.
- **Copernicus C3S:** ERA5 / ERA5-Land (also via Open-Meteo). "Contains modified Copernicus Climate Change Service information."
- **Copernicus EMS:** GloFAS.
- **Copernicus DEM GLO-30:** © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018, provided under COPERNICUS by the EU and ESA.
- **AWS Terrain Tiles:** DEM tiles.
- **Microsoft Global ML Building Footprints:** ODbL.
- **OpenStreetMap contributors:** ODbL.
- **GeoNames:** CC BY 4.0.
- **Sentinel-2 imagery** (landing page): "Contains modified Copernicus Sentinel data 2024–2025."
- **Wikimedia Commons photographs:** CC BY-SA, credited on the page.

**Software:** Python 3.12, pandas, NumPy, scikit-learn 1.7, XGBoost 3.2, SHAP 0.51, FastAPI, React 19, Vite 8, MapLibre GL 6, Recharts 3, Tailwind 4.
