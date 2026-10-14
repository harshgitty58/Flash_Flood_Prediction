# PRAHAR — Presentation Content & Technical Reference
*Predict · Prepare · Protect* — Uttarakhand flash-flood intelligence

Raw content blocks; arrange the flow yourself.
- **Part A** = the presentation story (slides).
- **Part B** = the complete technical reference (every component, parameter and design decision), for backup slides, viva questions and the report.

Every number comes from the repo outputs (`results/`) of the last full run: **pipeline audit 0 failures, 29 automated tests passing**.

---

# PART A — PRESENTATION STORY

## A1. Title
- **PRAHAR**: an uncertainty-aware, multimodal flash-flood **nowcasting** and exposure platform for Uttarakhand
- Course: Data Science (TY Sem V), VIT
- One-liner: *We combine live rain-gauge data with district flood history and terrain to flag where flash-flood risk is elevated, say how sure we are, and show which buildings could be exposed.*

## A2. Problem
- Uttarakhand: steep Himalayan valleys, intense monsoon cloudbursts, settlements packed along rivers (Kedarnath 2013, Chamoli 2021, Dharali 2025).
- Flash floods give **minutes to hours** of warning; public outputs are usually district-level bulletins.
- Gaps: no uncertainty, no "where exactly", no link from hazard to **what gets hit**.

## A3. Objectives (course)
1. **Dataset curation & multi-source integration**: rainfall, river discharge, flood history, landslides, district indices.
2. **Transformation, cleaning, normalisation**: QA, alignment, feature engineering.
3. **Optimised multi-model training & evaluation**: LR, RF, XGBoost; tuning, feature selection, event-level validation.
4. **Uncertainty-aware & robust prediction**: calibrated probabilities, conformal confidence, SHAP explanations, sensor-failure robustness, warning tiers.

## A4. Data sources at a glance
| Source | Volume | Coverage |
|---|---|---|
| CWC hourly rainfall telemetry | 46,379 rows · 47 gauges (44 usable after QA) | 2022-01 → 2026-09 |
| CWC river discharge (15-min → hourly) | 90,303 rows · 7 gauges | 2023-06 → 2025-12 (1 gauge from 2022-08) |
| GSI landslide inventory | 5,443 points | historical |
| IMD flood event inventory | 121 events (29 district-events in 2022-23) | 1970 → 2023-08-26 |
| District indices (DFSI, flooded area %, fatalities, flood duration, population) | 13 districts | static |
| Label set 2022-25 (IMD + SANDRP + Sphere India SitReps + EM-DAT + curated news) | 96 events / 130 district-days | audit + external validation |
| Microsoft ML Building Footprints | 90,837 buildings near alert stations | current |
| OpenStreetMap | rivers/streams, 804 road segments, 99 bridges, 1,639 named landmarks | current |
| AWS Terrain Tiles (SRTM-based DEM, ~30 m) | 69 tiles at zoom 13 | ~2000 |

## A5. The data story: five silent bugs found by testing the data
- **Timestamps:** hours 0-9 had no leading zero and were silently dropped → **47 % of all rainfall rows lost**.
- **Offline vs dry:** months-long gauge outages were being filled as "0 mm" → **58 % of the hourly grid** was fake dry weather.
- **Label timing:** the target labelled the day *before* each flood; the flood day's rain was labelled "no flood".
- **Faulty gauges:** a gauge with a median of 272 mm/h (physically impossible) was producing fake EXTREME alerts.
- **District names in the label join:** IMD writes *Rudra Prayag*, *Udam Singh Nagar*, *Garhwal*; stations use *Rudraprayag*, *Udham Singh Nagar*, *Pauri Garhwal* → **13 of 29 flood days (45 %) silently dropped**; Rudraprayag had 0 positives.
- Plus: telemetry error codes, duplicate station-hours, same-day leakage in history features. All now guarded by tests and an audit.

## A6. Where the datasets meet
- Rainfall 2022 → 2026 · discharge 2023-06 → 2025-12 · flood labels → 2023-08-26.
- **Training window A: 2022-02 → 2023-08-25.** All three sources overlap only Jun-Aug 2023 (too short alone).
- 2023-08 → 2026-09 is **replay**: the model runs, but there are no labels to score against.

## A7. Results (headline)
- **Fixing the label join** (bug 5) lifted XGBoost on the unseen test month from ROC-AUC 0.53 → **0.71**, PR-AUC 0.04 → **0.15**, F1 0.08 → **0.32**, MCC 0.06 → **0.30**.
- **Leave-one-event-out ROC-AUC 0.70**, now consistent with the test month (the earlier 0.86 was inflated: positives came from only 5 districts).
- **Hybrid warning** at ≥ ALERT on the test month: precision **0.23**, recall **0.65**, F1 **0.34** (ML alone 0.22 / 0.57).
- **Label audit:** SANDRP documents **40 damaging events that IMD misses** (vs 26 IMD events). Scored against that fuller answer key, the same model's district-day CSI rises 0.15 → 0.20.
- **External validation:** 29 documented events after Aug 2023; hybrid ≥ ALERT POD **7/21 = 0.33** [0.14, 0.52] where a gauge was reporting.
- **Honest:** the ML tier over-alerts in replay (~18 % of hours ≥ ALERT); the model is good at *where*, weak at *which hour*.

## A8. The platform
- 10-page web app with a dark-forest glass UI, satellite/terrain/3D maps, building-level exposure, explanations, metrics and system health.
- FastAPI backend: live prediction, what-if scenarios, ~1 ms data endpoints.
- Latency engineering: buildings per map view **22.8 MB → ≤ 0.7 MB**, feature update **O(1)**, calibration **~1000× faster**.

## A9. Demo script (3 min)
1. Landing → "Replay a real event" → Overview: EXTREME at Haldwani, **141 mm in 24 h** (set by the rainfall rule); 7 stations ≥ SEVERE; 45k buildings exposed.
2. Risk Map → Satellite → Pithoragarh: drawer shows *IMD rainfall SEVERE vs ML NORMAL*, so the rule layer catches what the model misses.
3. Impact → fly to Haldwani → building outlines coloured by exposure → click a building for its score breakdown.
4. Metrics: Ground-truth panel (label fix before/after, IMD vs SANDRP audit, v2 decision); hybrid recall 0.65; external-validation table with sources (Kedarnath route 2024: warning switched on ~44 h before).
5. System: every service green; latency table.
6. Close: the data story + honest limits.

## A10. What makes it different
- Multimodal fusion quantified by ablation, not claimed.
- Hybrid warning: learned district-risk model + transparent IMD rainfall rules, with the trigger shown per station.
- Uncertainty and data-source health beside every prediction.
- Hazard → **building-level exposure** using pretrained-model footprints + terrain.
- Built honestly: replay mode, external validation with sources, limitations on screen, audited pipeline.

## A11. Honest limitations (say it before they ask)
- **Nowcasting, not forecasting:** no weather-forecast input.
- **Labels:** 29 district-level IMD *dates* (2022-23); every gauge in a district is marked "flood". IMD misses ~60 % of SANDRP-documented hill events; adding them to training (label v2) did **not** help on the test month, so it was not adopted.
- **ML tier ≈ district prior:** some gauges are at ALERT > 95 % of hours.
- **Lead time not claimed:** genuine "warning switched on before the event" observed only twice (Kedarnath route 2024 ~44 h, Haridwar 2024 ~4 h).
- Rainfall rule over-alerts in some months (July 2023 precision 0.01).
- Impact score is a hand-tuned exposure proxy; DEM ~30 m from ~2000.

## A12. Responsible use / what we don't claim
- Not structural damage, monetary loss, casualties or evacuation orders.
- No guaranteed arrival times or lead times; feature importance is not causation.
- Decision support for analysts; every output is an estimate with stated uncertainty.

## A13. Closing line
> **PRAHAR: from "82% flood probability" to "this district, this rainfall, these buildings along this river, with this much confidence."**

---

# PART B — TECHNICAL REFERENCE

## B1. System architecture
```
curated_dataset/ (raw CSVs)
   │  src/cleaning.py            parse · QA flags · sentinel/faulty-gauge removal · dedup
   ▼
data/processed/cleaned/*.parquet
   │  src/rainfall_features.py   hourly grid · offline gaps · clock-hour windows · API
   │  src/discharge_features.py  deltas · rolling stats · anomaly
   │  src/spatial.py             landslide proximity/density per gauge
   │  src/flood_features.py      past-only district flood history
   │  src/target.py              label: flood in district today/tomorrow · label coverage
   ▼
data/processed/final/uttarakhand_flash_flood_ml_dataset.parquet   (518,304 station-hours)
   │  notebooks 09-14 (= src modules)
   │    09 data window · normalisation · splits     10 train LR/RF/XGB
   │    11 leave-one-event-out CV + lead time       12 Venn-Abers + conformal
   │    13 hybrid warning tiers + external valid.   14 SHAP · robustness · metrics · report
   ▼
results/  (models, predictions, conformal, warning levels, SHAP, robustness, metrics, reports)
   │  scripts/export_frontend_data.py   → web/public/data/*.json (strict JSON)
   │  scripts/build_impact_layer.py     → buildings + landmarks scored (MS footprints, OSM, DEM)
   │  scripts/build_building_tiles.py   → adaptive quadtree tiles
   ▼
backend/app.py (FastAPI)  ◄──►  web/ (React + MapLibre)
   checks: pytest (29) · scripts/bench_latency.py · scripts/check_apis.py · scripts/audit_pipeline.py
   orchestration: scripts/run_notebooks.py · scripts/run_all.py
```

## B2. Data sources (detail)
| Source | Raw format | Key fields | Notes |
|---|---|---|---|
| CWC telemetry rainfall | 2 CSVs (2021-25, 2026-30), 46,379 rows | station, district, lat/lon, `Data Acquisition Time` (`DD-MM-YYYY H.MM`), hourly rain (mm) | Only rainy hours are logged (min 0.5 mm, no zeros) |
| CWC river discharge | hourly curated CSV, 90,303 rows | station, datetime, discharge | 7 gauges: Karnaprayag, Kheri_5, Koteshwar, Lambagarh, Marchula_1, Rudraprayag_3, Tekhla |
| GSI landslide inventory | CSV, 5,443 points | lat/lon, district, movement history | 5,417 after coordinate checks |
| IMD flood inventory | CSV, 121 events | start/end date, districts, cause, fatalities | Expanded to 334 district-event records (multi-district events) |
| District indices | 3 CSVs × 13 districts | DFSI, corrected % flooded area, fatalities, injured, population, mean flood duration | Static |
| Curated 2024-25 events | `supplement_2024_2025.csv`, 12 rows | date, district, place, type, date confidence, source URL | Evaluation only, never training |
- The pipeline reads `flash-flood-prediction/curated_dataset/`; the repo also ships `curated_dataset/`. A test asserts both copies are **byte-identical** (MD5).
- District names are standardised through a master crosswalk (`src/district_mapping.py`) across all sources.

## B3. Cleaning rules (`src/cleaning.py`)
- **Timestamp parsing:** `'06-10-2022 0.00'` → regex zero-pads the hour → `%d-%m-%Y %H:%M:%S`; floored to the hour. Parse rate 100 % (was 53 %).
- **Quality flags** (in order): `missing` · `negative_invalid` (< 0) · `sentinel` (= **511.5**, telemetry error code) · `faulty_station` · `implausible` (> **150 mm/h**) · `valid`. Only `valid` becomes `rainfall_clean`; everything else is NaN (never 0).
- **Faulty-gauge quarantine:** a station is quarantined if > **20 %** of its non-sentinel readings exceed 100 mm/h → Yamuna Colony (median 272 mm/h), Roorkee_2, Purola_1.
- **Duplicates:** per (station, hour) keep the maximum valid reading.
- Result: 40,640 rows → 33,377 valid, 5,960 faulty-station, 794 sentinel, 443 implausible, 66 negative.
- Discharge: sentinels/negatives flagged; per-hour completeness kept. Landslides: out-of-bounds coordinates removed. Flood inventory: district-level only (no fake point precision).

## B4. Building the hourly table (`src/rainfall_features.py`, `src/pipeline.py`)
- **Hourly grid:** each gauge expanded from first to last record; absent hours = **0 mm** (gauges log only rainy hours).
- **Offline detection:** silences longer than **7 days (Jun-Sep)** or **45 days (other months)** are outages → those hours are removed (not "dry"). 535 outage gaps removed; 58 % of the naive grid was outage time.
- **One coordinate per gauge:** most frequent lat/lon (Almora_1 reported two coordinate pairs, which previously duplicated its rows).
- **Joins:** landslide features by station; district indices by district; discharge features averaged per (district, hour).
- Final table: **518,304 station-hours · 44 gauges · 42 columns**; 126,904 labelled rows (24.5 %), **895 flood hours**.

## B5. Features
| Group | Features | Definition |
|---|---|---|
| Rainfall (10) | `rain_1h`, `rain_3h`, `rain_6h`, `rain_12h`, `rain_24h`, `rain_48h`, `rain_72h` | backward **clock-hour** rolling sums (time-based windows, so outages are never bridged) |
| | `rain_max_intensity_24h` | max hourly rain in the last 24 h |
| | `rain_intensity_change_1h` | rain(t) − rain(t−1) |
| | `api_decay_85` | antecedent precipitation index, API_t = 0.85·API_{t−1} + P_t |
| Discharge (4) | `discharge_clean`, `discharge_change_1h/3h`, `discharge_anomaly` | diffs; anomaly = value − station mean |
| District susceptibility (5, static) | DFSI, flooded area %, historical fatalities, mean flood duration, population | from district tables |
| Landslide / terrain (4) | `dist_to_nearest_landslide_km`, `landslide_count_5km`, `landslide_count_10km`, `is_landslide_hotspot` | haversine to GSI points; hotspot = ≥ 5 landslides within 10 km |
| Removed from final model | lat/lon · calendar (hour, weekday, day of year, month, monsoon flag) · `historical_flood_count_prior_t`, `days_since_last_flood_prior_t` | coordinates memorise locations; counters drift once labels stop (2023-08) |
- **Leakage controls:** past-only windows; flood history counts only floods on *earlier calendar days*; imputation/normalisation fitted on train only; thresholds frozen on validation; 7-day buffer around held-out events.

## B6. Target definition (`src/target.py`)
- IMD gives flood **dates** (stored 00:00), not times.
- **y(t) = 1** if a flood is recorded in the gauge's district on t's calendar day **or the next day**; else 0.
- Earlier "start within next 24 h" definition put labels on the day *before* the flood (flood-day hours: 4 % labelled; rain 3× normal on the flood day) → fixed.
- **Label coverage:** rows whose window extends past the last inventory date (2023-08-26) are **NaN = unlabelled**: excluded from training/metrics, used for replay only.

## B7. Study window, splits and normalisation
- **Coverage analysis** (`src/data_window.py`) → `results/data_audit/coverage_matrix.csv` + heatmap; windows in `results/data_windows.json`:
  - A (train): 2022-02-01 → 2023-08-25 · B (all three sources): 2023-06-07 → 2023-08-25 · C (sensor overlap, needs labels): 2023-06-07 → 2025-12-31 · replay: 2023-08-26 →.
- **Splits** (`results/splits.json`): train ≤ 2023-06-30 (94,154 rows, 367 flood hours, 37 gauges) · validation Jul 2023 (20,280 / 864 / 35) · test Aug 1-25 2023 (12,469 / 720 / 29). (Before the label-join fix: 271 / 384 / 240.)
- **Normalisation** (`src/normalization.py`, `FeatureNormalizer`, saved to `results/preprocessing/normalization_params.json`, reused by the API):
  - `log_robust` (rain, API, discharge, landslide counts, population, fatalities): (log1p x − median) / IQR (std if IQR = 0)
  - `signed_log` (rain/discharge changes, anomaly): (sign(x)·log1p|x| − median) / IQR
  - `zscore` (DFSI, flooded area %, flood duration, distance to landslide): (x − mean) / std
  - `passthrough` (binary hotspot flag)
- Pipeline per model: `SimpleImputer(median)` → `FeatureNormalizer` → classifier.

## B8. Models and tuning (`src/tune_models.py`, `src/train_pipeline.py`)
- Search: `RandomizedSearchCV`, **8 iterations**, `TimeSeriesSplit(n_splits=3)`, scoring = balanced accuracy, fitted on train only.
| Model | Search space | Selected |
|---|---|---|
| Logistic Regression | C ∈ {0.01, 0.1, 1, 5, 10}; solver ∈ {lbfgs, liblinear}; class_weight ∈ {balanced, None} | C = 1.0, lbfgs, balanced |
| Random Forest | trees {100, 200}; depth {5, 10, 15, None}; min split {2, 5, 10}; min leaf {1, 2, 4}; class_weight {balanced, balanced_subsample, None} | 200 trees, depth None, min split 5, leaf 1 |
| **XGBoost (deployed)** | trees {100, 200}; depth {3, 5, 7}; lr {0.01, 0.05, 0.1}; subsample {0.8, 1.0}; colsample {0.8, 1.0}; scale_pos_weight {1, neg/pos} | 100 trees, depth 5, lr 0.01, subsample 0.8, colsample 1.0, **scale_pos_weight 346** |
- **Threshold:** swept 0.05 → 0.95 (19 steps) on validation; pick max F1 among thresholds with recall ≥ 0.20 (else max F1); frozen before test.
- **Feature-set experiments** (A rainfall only → B + discharge → C + flood history → D + landslide → E + season & lat/lon → F = E minus lat/lon → **G = D minus drifting counters (deployed, 23 features)**).

## B9. Evaluation protocol
- **Leave-one-event-out CV** (`src/event_cv.py`): flood days merged into episodes when ≤ **4 days** apart (6 episodes); each held out with test window **±3 days** and training excluding **±7 days**; XGBoost with the tuned parameters; out-of-fold predictions pooled.
- **Chronological test:** single pass on Aug 2023 at the frozen threshold.
- **Metrics** (`src/evaluate.py`, `src/metrics_report.py`): precision, recall, F1, specificity, balanced accuracy, MCC, ROC-AUC, PR-AUC (average precision), Brier, log loss, confusion matrix, false alarms per station-month, PR/F1-vs-threshold curve.
- **Event-level detection:** alarm threshold = 95th percentile of out-of-fold scores on non-flood hours (5 % hourly false-alarm rate); an event is detected if a gauge in its district crosses it within 48 h before the event day.

## B10. Results (full)
**Leave-one-event-out (6 episodes, 1,248 flood hours, base rate 8.1 %; after the label-join fix)**
| Feature set | ROC-AUC | PR-AUC | Min per-episode ROC |
|---|---|---|---|
| A Rainfall only | 0.497 | 0.093 | 0.35 |
| B + Discharge | 0.548 | 0.101 | 0.45 |
| C + Flood history | 0.772 | 0.223 | 0.63 |
| D + Landslide/terrain | 0.772 | 0.236 | 0.57 |
| E + Season & lat/lon | 0.655 | 0.141 | 0.50 |
| **G deployed (23 features)** | **0.701** | 0.186 | 0.58 |
| H multisource (ERA5, soil, terrain) | 0.703 | 0.147 | 0.58 |
| T trigger-only | 0.602 | 0.104 | 0.47 |
- C/D score higher, but they depend on IMD flood-history counters that stop updating when the inventory ends (2023-08), so they can't be deployed for 2024+. G stays deployed.
- Before the fix, G scored 0.858. That was inflated: every positive came from 5 districts.

**Hour level, frozen threshold (after the fix; before → after on test in `results/label_impact.md`)**
| Model | Split | Precision | Recall | F1 | MCC | ROC-AUC | PR-AUC |
|---|---|---|---|---|---|---|---|
| Logistic Regression | val (Jul 23) | 0.124 | 0.219 | 0.158 | 0.115 | 0.642 | 0.076 |
| Logistic Regression | test (Aug 23) | 0.169 | 0.211 | 0.188 | 0.133 | 0.741 | 0.139 |
| Random Forest | val | 0.150 | 0.358 | 0.212 | 0.179 | 0.632 | 0.113 |
| Random Forest | test | 0.173 | 0.369 | 0.236 | 0.185 | 0.788 | 0.152 |
| XGBoost | val | 0.139 | 0.366 | 0.201 | 0.170 | 0.719 | 0.109 |
| XGBoost | test | 0.222 | 0.574 | 0.320 | 0.295 | 0.708 | 0.150 |
- XGBoost test confusion matrix: TP 413 · FP 1,445 · FN 307 · TN 10,304.

## B11. Uncertainty (`src/conformal.py`)
- **Venn-Abers calibration (inductive):** for each score, isotonic regression fitted on calibration scores + (s, 0) and + (s, 1) → interval [p0, p1]; calibrated p = p1 / (1 − p0 + p1). Calibration set = validation predictions (20,280 rows, 384 floods).
- **Speed-up:** p0/p1 computed exactly on a **400-point** score grid and linearly interpolated (exact per-score refits were too slow for ~1M replay rows).
- **Mondrian (class-conditional) conformal prediction** on calibrated p: non-conformity = 1 − p(class); p-values within each class's calibration scores; **confidence** = 1 − second-largest p-value, **credibility** = largest; prediction sets at 80 / 90 / 95 % → FLOOD / NO_FLOOD / UNCERTAIN.
- Results (test, after the label fix): Brier 0.093 → **0.052**; 90 % sets cover 93.9 % overall, **87.5 %** of flood hours (slightly under target), 90.8 % of sets UNCERTAIN.
- Caveat: conformal guarantees assume exchangeability, which time series from a different month violate.

## B12. Hybrid warning tiers (`src/warning_levels.py`)
- **ML tier** on calibrated p, cut-offs = multiples of the calibration base rate (1.893 %): WATCH ≥ 2× (3.79 %), ALERT ≥ 5× (9.47 %), SEVERE ≥ 10× (18.9 %), EXTREME ≥ 20× (37.9 %). A 90 % conformal set of {FLOOD} lifts it to ≥ ALERT.
- **Rainfall tier** (IMD categories on the gauge's own rain): moderate ≥ 15.6 mm/24 h → WATCH; heavy ≥ 64.5 → ALERT; very heavy ≥ 115.6 → SEVERE; extremely heavy ≥ 204.5 mm/24 h or cloudburst ≥ 100 mm/1 h → EXTREME. Susceptibility adjustment for levels ≥ heavy: **+1** if landslide hotspot *and* district DFSI ≥ median (13.93), **−1** if neither (min WATCH, max EXTREME).
- **Final tier = max(ML tier, rainfall tier)**; `trigger` = ml / rainfall / none.
- ≥ ALERT on the test month: ML 0.22 precision / 0.57 recall; rainfall 0.38 / 0.08; **hybrid 0.23 / 0.65** (F1 0.34, false-alarm rate 13 %). On validation the rainfall layer over-alerts (precision 0.02). Re-tuning the rule on validation (`src/tier_tuning.py`, 32 rules) found nothing better than the default beyond noise, so the IMD default is kept.
- Base rate after the fix 4.26 % → ML cut-offs WATCH 8.5 % · ALERT 21.3 % · SEVERE 42.6 % · EXTREME 85.2 %.
- Replay distribution (391k hours, 2023-08 → 2026-09): NORMAL 76 % · WATCH 5 % · ALERT 18 % · SEVERE 0.8 % · EXTREME 0.3 %. The ML tier now over-alerts in high-prior districts (planned fix: district-day model, LABELS_PLAN L5).

## B13. External validation (`src/external_validation.py`)
- Events: rows of `data/external/labels/labels_2022_2025.csv` dated after the IMD coverage end → **29 events (2023-09-15 → 2025-09-17)**, 21 with a reporting gauge in the district.
- Hybrid ≥ ALERT POD **7/21 = 0.33** (95 % CI 0.14–0.52); ML-only 3/21; rainfall-only 6/21. Detected: Kedarnath route and Haridwar (31 Jul 2024), Champawat/Chamoli/Pauri (8 Jul 2024), Dharali (5 Aug 2025), Yamunotri highway (29 Jun 2025).
- 8 events had **no reporting CWC gauge** (e.g. Dehradun 15 Sep 2025). Next lever: fill these with USDMA hydromet stations.
- **Alert burden** (a false-alarm proxy; a true FAR needs a complete event list): 329 ALERT district-days in monsoon 2024, 4 % of them within ±2 days of a documented event; 164 in 2025 (5 %).

## B25. Ground truth and label audit (`scripts/build_labels.py`, `src/label_audit.py`, `src/label_experiment.py`)
- **Sources:** IMD inventory (29 district-days 2022-23) · SANDRP Uttarakhand cloudburst compilations 2022 and 2023 (52) · Sphere India situation reports (hand-checked, 44) · EM-DAT (25) · curated news list (14). Merged (same district within ±1 day) into **96 events / 130 district-days**; 22 confirmed by ≥ 2 sources; 1 exclusion (lightning only). Every row keeps its source reference and a date confidence.
- **Audit (2022 – Aug 2023):** SANDRP reports 48 events and IMD 26. Only 8 of 28 IMD days appear in SANDRP, which lists hill cloudbursts, not plains floods. **40 SANDRP events are missing from IMD** (22 in train, 8 in validation, 12 in test). On 5 of the 20 validation/test ones the hybrid had already alerted, and v1 scored that as a false alarm.
- **Label v2 experiment** (IMD ∪ SANDRP ∪ SitReps; same features, splits and tuned parameters; 2×2 train-label × truth grid; adoption rule fixed in advance): event-CV improves (ROC 0.70 → 0.78), but the v2-trained XGBoost is worse on the test month against both answer keys (PR-AUC 0.113 vs 0.150 on IMD truth), so **v2 is not adopted**. As an answer key, v2 shows the deployed model is better than the IMD labels say: PR-AUC 0.150 → 0.206, district-day CSI 0.150 → 0.197, FAR 0.82 → 0.72.
- Full before/after: `results/label_impact.md`. Plan and next levers: `LABELS_PLAN.md`.

## B26. Model upgrade experiments (`src/ensemble.py`, `src/rain_thresholds.py`, `src/district_pooled.py`)
- **E1 ensemble** (LR + RF + XGBoost, percentile-averaged): test ROC-AUC 0.71 → 0.78, event-CV PR-AUC 0.19 → 0.21, but district-day CSI is unchanged or slightly lower, so it is not adopted.
- **E2 rainfall thresholds fitted on 46 documented events:** half the floods had < 50 mm/24 h at the district's wettest gauge. Fitted thresholds catch more 2025 events (5/10 vs 2/10) but double the alerts and halve CSI, so they are not adopted. This shows the gauge network misses local cloudbursts.
- **E3 pooled district-day model:** not adopted as an alert layer. As a **daily ranking** it beats district history: the flooded district was in the top 3 for 34 % of documented events, vs 21 % for district history alone (chance 23 %). Shown on Overview as "Districts to watch".
- **Conclusion:** the limit is labels and rain observation, not the model class. Next steps are data (USDMA SEOC reports, radar/IMERG rain).

## B14. Explainability and robustness
- **SHAP** (`src/explain.py`, TreeExplainer on the deployed XGBoost, test + replay rows): mean |SHAP| — district mean flood duration 0.99 · rain_48h 0.23 · DFSI 0.21 · distance to landslide 0.13 · API 0.04 · 24 h peak intensity 0.03 · rain_72h 0.03. Top-3 signed drivers stored per prediction and shown in the station drawer.
- **Robustness** (`src/robustness.py`, inference-time degradation on val + test, no retraining):
| Scenario | ROC-AUC | PR-AUC |
|---|---|---|
| Baseline | 0.554 | 0.042 |
| Rainfall noise σ = 5-50 % of std | 0.574-0.578 | 0.034-0.037 |
| River discharge offline | 0.554 | 0.042 (no effect) |
| Rainfall gauge offline | 0.470 | 0.025 |
| Flood-history records unavailable | 0.500 | 0.019 |
| Landslide inventory unavailable | 0.542 | 0.040 |
| Random 10 / 25 / 50 % input dropout | 0.538 / 0.526 / 0.500 | 0.033 / 0.028 / 0.022 |
| Noisy rain + discharge offline | 0.573 | 0.036 |

## B15. Impact / exposure engine (`scripts/build_impact_layer.py`, audited by `scripts/audit_impact.py`)
1. **Hazard centres** (each building takes the nearest centre's tier):
   - **live gauges:** 27 reporting at the replay hour (12 Sep 2024, 19:00), 5 km radius, solid outlines;
   - **offline gauges:** 3 with a report in the last 7 days (dashed);
   - **ungauged towns and Char Dham sites:** 40, 3 km radius (dotted). The tier comes from the district-day ranking (top 3 → ALERT, 4–6 → WATCH), and the district comes from GeoNames' district codes. These never count in exposure totals.
2. **Buildings:** Microsoft Global ML Building Footprints (polygons from imagery by Microsoft's pretrained segmentation model), India quadkey files (zoom 9), regex pre-filter → **575,339 buildings**.
3. **Rivers / landmarks:** OpenStreetMap via Overpass, chunked (live areas: rivers, roads and 9 named-feature keys; new areas: rivers only), mail.ru mirror first, cached. **Place names:** GeoNames (11,589 towns, villages and hamlets, state-wide).
4. **Class = official river-setback zone × hazard tier** (no home-made weights):
   - zone **A ≤ 50 m:** NGT 2017, no construction in the hills; active flood plain;
   - zone **B 50–100 m:** NGT regulatory zone, and the Jal Shakti 2025 interim 100 m no-development zone;
   - zone **C 100–200 m:** Uttarakhand High Court 2013, no construction within 200 m of any river;
   - the class is the tier level in A, one lower in B, two lower in C, and MINIMAL beyond 200 m.
5. Height above the river (Terrarium DEM, z13) is **shown for information only**. The official flood plain is the 1-in-100-year highest flood level + 1 m (Uttarakhand Flood Plain Zoning Act 2012), and those maps aren't public.
6. **Audit:**
   - all 575,339 buildings match zone × tier (0 mismatches);
   - Haldwani (EXTREME, 140.5 mm): 2,149 CRITICAL (zone A), 1,942 HIGH (B), 3,387 MODERATE (C);
   - flagged, not overridden: 4 dry-day ML-prior ALERTs (Joshiyara 3 mm, Sonprayag 0 mm, Chakrata 15.5 mm, Chandranagar 0.5 mm);
   - flagged: 13 plains areas where > 30 % of buildings are > 2 km from any mapped river (waterlogging, which a river-setback rule can't capture).
- Live-gauge totals: 261,030 buildings; 2,149 CRITICAL, 2,806 HIGH, 5,342 MODERATE.

## B16. Backend API (`backend/`, FastAPI + Uvicorn)
- **Startup:** loads model, normalisation, calibration lookup, per-station history index, and every exported JSON into memory (~0.9 s).
- **Inference engine** (`backend/inference.py`): O(1) feature update per new reading (B18) → XGBoost → Venn-Abers via `np.interp` on the precomputed 400-point grid → conformal p-values by `searchsorted` on pre-sorted calibration scores → hybrid tier.
- **Endpoints:** `GET /health`, `/health/external` (10 services probed concurrently, cached 60 s), `/data/{name}`, `/stations`, `/risk/snapshot`, `/risk/timeline`, `/model/summary`, `/metrics`, `/events`, `/impact/summary`, `/impact/tiles/index`, `/impact/tiles/{z}/{x}/{y}`, `/landmarks`; `POST /predict` (station + hourly readings), `/predict/scenario` (what-if overrides, state untouched), `/admin/reload`. Interactive docs at `/docs`.
- **HTTP:** pre-serialised payloads with MD5 ETags (→ 304 Not Modified), GZip ≥ 1 KB, CORS, `X-Process-Time-ms` header on every response, `Cache-Control: max-age=86400` for tiles, typed Pydantic request models (rain 0-150 mm), 404 for unknown/quarantined stations.

## B17. Frontend (`web/`)
- **Stack:** React 19, TypeScript 6, Vite 8, Tailwind CSS 4, MapLibre GL 6, Recharts 3, React Router 7.
- **Pages (lazy-loaded):** Landing · Overview · Forecast (replay timeline) · Risk Map · Impact · Uncertainty · Events · Data & Model · Metrics · System.
- **Map (`FloodMap.tsx`):** CARTO dark-matter vector basemap tinted forest-green; Esri World Imagery (satellite); OpenTopoMap (terrain); AWS Terrarium hillshade + optional 3D terrain (exaggeration 1.5); Esri place-label overlay; landmark symbol layer (Montserrat glyphs); pulsing HTML station markers sized by probability; building outlines coloured by a score step expression; landslide layer; hover → nearest place + coordinates.
- **Data layer (`lib/data.ts`):** cached `useData` hook; static JSON or API (`npm run dev:api` → Vite proxy `/api` → :8000 via `.env.api`); in-flight request counter.
- **UX:** glass sidebar with grouped navigation (Situation / Analysis / Validation / Platform), glass header with breadcrumb, river-flow page transition (~0.7 s every route change, non-blocking) plus a loader for fetches > 200 ms, page fade-in, forest theme tokens, strict-JSON-safe rendering.
- **Station drawer:** final tier and trigger (ML vs IMD rainfall), calibrated probability, raw score, confidence, 90 % set, top-3 SHAP drivers, rainfall/terrain signals.

## B18. Latency engineering (`scripts/bench_latency.py`, latest run)
| Path | Old | New | Algorithm |
|---|---|---|---|
| Buildings for one map view | one 22.8 MB GeoJSON, ~432 ms to parse | ≤ 0.7 MB tile (~104 KB gzipped), ~56 ms | **adaptive quadtree tiling**: z12 tiles split recursively until ≤ 3,000 buildings (max z15); client loads only tiles in view (zoom ≥ 11) and caches them; overview markers below that |
| Rain features per station-hour | 0.46 ms batch recompute | **0.034 ms** | **O(1) incremental state**: 72-h ring buffer with running window sums, monotonic deque for the 24-h max, recursive API; verified identical to batch over 3,000 hours |
| Calibrate one score | 1.7 ms (2 isotonic fits) | **0.002 ms** | precomputed Venn-Abers lookup table |
| `POST /predict` | — | ~6.6 ms p50 | above + per-station history index (no full-table scan) |
| Data endpoints | — | ~1 ms; ~0.5 ms cached | in-memory blobs + ETag/304 + gzip |
| Impact layer rebuild | 25+ min, died on a DNS error | ~1 min | regex pre-filter + vectorised Shapely 2 + retry/backoff + caching |
| Map page bundle | single bundle | per-page chunks | lazy routes; full building file no longer shipped |
(Absolute timings vary run to run; ratios are stable.)

## B19. Testing and verification
- **29 automated tests** (`pytest -q tests`):
  - Data contracts (12): raw copies identical · every timestamp parses · single-digit hours · no invalid rain survives · no duplicate station-hours · rain windows are clock hours · labels inside inventory coverage · flood day + day before labelled · history uses only earlier days · final features present and non-drifting · normaliser round-trip · splits recorded and disjoint.
  - Online features (1): O(1) features equal batch features over 3,000 hours.
  - API (16 incl. parametrised): health · 10 data endpoints (200 + ETag + < 200 ms) · ETag → 304 · tiles listed exist · `/predict` contract and < 50 ms · cloudburst scenario → SEVERE/EXTREME · unknown station → 404 · (network-marked) external services reachable.
- **Pipeline audit** (`scripts/audit_pipeline.py`): raw parse rate; byte-identical data copies; cleaned output newer than raw; no valid rain > 150 mm/h; no duplicates; hourly grid contiguous within segments; label coverage; final features present; models newer than data with matching feature names; predictions newer than models and replay rows = unlabelled rows; every Phase-4 artefact fresh; all exports present and **strict JSON (no NaN)**; impact layer and snapshot share the replay time; every page's data source exported; building tiles indexed and present; full building file not shipped. Result: **0 failures**.
- **External API checker** (`scripts/check_apis.py`): CARTO style + glyphs, Esri imagery + labels, AWS terrain, OpenTopoMap, Overpass (2), Microsoft footprints index, Google Fonts + local API; 9/10 up (one Overpass mirror down; covered by fallback).

## B20. Reproducibility and operations
```bash
python -m pip install -r requirements.txt              # pinned (pandas 2.3, xgboost 3.2, scikit-learn 1.7, shap 0.51, shapely 2.2, fastapi 0.135 …)
python scripts/run_notebooks.py                         # notebooks 09-14 headless, outputs saved, timings → results/notebook_runs.csv
python scripts/run_all.py --from export                 # export → impact → tiles → tests → bench → apis → audit
python -m uvicorn backend.app:app --port 8000           # API
cd web && npm install && npm run dev:api                # frontend on :5173 (or `npm run dev` for static mode)
```
- Fixed random seeds; every artefact regenerated from raw data by one command; `run_all.py` stops at the first failing stage.
- Notebooks 01-08 = Objectives 1-3 history; 09-14 = current executed record.

## B21. Repository layout
| Path | Contents |
|---|---|
| `src/` (31 modules) | cleaning, features, target, splits, normalisation, training, event CV, conformal, warning levels, external validation, SHAP, robustness, metrics, reports, online features |
| `backend/` | `app.py` (FastAPI), `inference.py` (low-latency engine) |
| `scripts/` | export, impact layer, tiling, notebooks runner, run_all, audit, API checker, latency benchmark |
| `tests/` | data, online-feature and API tests |
| `notebooks/` | 01-14 |
| `web/src/` | pages (10), components (map, drawer, object card, loader, UI kit), data layer |
| `results/` | models' predictions, metrics, reports (`phase4_report.md`), coverage, splits, latency, impact layer |
| Docs | `README.md`, `EXECUTION_PLAN.md`, `REMAINING_TASKS.md`, this file |
- Size: ~4,800 lines of Python (src, backend, scripts, tests) and ~1,600 lines of TypeScript/TSX.

## B22. Known technical limitations (full list)
1. **Nowcasting only:** no numerical weather forecast input; the "Forecast" page plots past replay predictions.
2. **Label noise:** district-level dates; every gauge in the district labelled.
3. **ML tier ≈ district prior:** Dakpathar 100 %, Joshiyara 98 %, Doiwala 95 % of replay hours at ALERT+.
4. **Optimistic event-CV:** feature set selected on the same folds; folds also train on post-event data.
5. **Lead time not measurable as implemented:** saturates the 48 h search window when an alarm is permanently on.
6. **IMD categories applied to rolling 24 h** (IMD uses 08:30-08:30 daily totals); cloudburst defined over ~20-30 km², applied at one gauge.
7. **Calibration seasonally biased** (July calibration month); conformal coverage below target for floods; 80 % and 90 % sets identical (coarse p-values).
8. **Impact proxy:** nearest mapped stream ≠ drainage-connected HAND; nearest gauge ≠ upstream catchment; DEM ~30 m, ±5-10 m vertical, ~2000; weights not calibrated on damage.
9. **Discharge unused:** 7 gauges, district-mean matching.
10. **No labels after 2023-08** beyond 12 curated major events.
11. **Map rendering:** ~45k polygons render slowly without a GPU; main JS chunk 1.3 MB.

## B23. Roadmap
- **Metrics:** lead time from alert switch-on; ML alerts relative to each station's baseline; nested CV.
- **Labels:** curate all flood days 2023-09 → 2025-12 (or an official SDMA log) → train on window C (all sensors).
- **Rules:** per-district, per-season thresholds; IMD daily-window alignment.
- **Forecasting:** add IMD/GFS rainfall forecasts.
- **Data:** Copernicus GLO-30 / ALOS 12 m DEM, SMAP / ERA5-Land soil moisture, GPM IMERG satellite rainfall; upstream-catchment discharge matching.
- **Inundation:** HAND-based extent and depth replacing the exposure proxy.
- **Platform:** PostgreSQL + PostGIS, PDF situation reports, email alerts, login roles, Docker + CI, deployment.

## B24. References & attributions
- Research basis: 12 papers listed in the course document (uncertainty-aware ML for flash floods, ML4FF, explainable flash-flood models, LSTM inundation forecasting, Mahanadi ML comparison, transfer learning for data-scarce regions, etc.).
- Data: CWC, IMD, GSI · Microsoft Global ML Building Footprints (ODbL) · © OpenStreetMap contributors (ODbL) · Esri imagery & labels · CARTO basemap · AWS Terrain Tiles (SRTM) · OpenTopoMap · event sources in `curated_dataset/flood_inventory/supplement_2024_2025.csv`.
- Methods: Venn-Abers predictors (Vovk et al.), Mondrian conformal prediction, SHAP TreeExplainer (Lundberg & Lee), XGBoost (Chen & Guestrin), IMD rainfall categories.
