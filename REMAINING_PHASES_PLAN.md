# Uttarakhand Flash-Flood Prediction — Remaining Phases Plan

> **Current Status:** Objectives 1, 2, and 3 are complete.  
> **Selected Candidate Model:** XGBoost (Exp E — Full Multimodal) · Val ROC-AUC **0.9299** · Val PR-AUC **0.3124**  
> **This document covers:** Phase 4 (Objective 4) and Phase 5 (Frontend Dashboard)

---

## Quick Status Recap

| Objective | Phase | Status | Key Output |
|:---|:---|:---:|:---|
| 1 — Data Curation | Phase 1 | ✅ Done | `flash-flood-prediction/curated_dataset/` |
| 2 — Transformation & Feature Engineering | Phase 2 | ✅ Done | `data/processed/final/uttarakhand_flash_flood_ml_dataset.parquet` (21,982 rows × 42 cols) |
| 3 — Multi-Model Training & Evaluation | Phase 3 | ✅ Done | 3 trained models, full evaluation suite |
| 4 — Uncertainty-Aware & Robust Prediction | Phase 4 | ⏳ **Next** | Conformal prediction, SHAP, robustness, warning levels |
| 5 — Frontend Dashboard | Phase 5 | ⏳ After Phase 4 | Interactive map + live flood risk panel |

---

# Phase 4 — Objective 4: Uncertainty-Aware and Robust Flood Prediction

## Goal

Take the frozen XGBoost candidate from Phase 3 and wrap it with:
1. **Uncertainty quantification** via Conformal Prediction (CP)
2. **Interpretability** via SHAP values per prediction
3. **Robustness experiments** — what happens when sensors go offline or readings are noisy?
4. **Operational warning levels** — translate raw probability + uncertainty into actionable alert tiers

---

## Phase 4 Architecture

```
Frozen XGBoost (Exp E) + Phase 3 Artifacts
            │
   ┌─────────┴─────────────────────────────┐
   ▼                                       ▼
Step 4A                               Step 4B
Conformal Prediction                  SHAP Interpretability
(Calibration + Prediction Sets)       (Global + Local Explanations)
   │                                       │
   └─────────────┬─────────────────────────┘
                 ▼
             Step 4C
         Robustness Experiments
   (Noise injection, sensor outages, missing data)
                 │
                 ▼
             Step 4D
      Operational Warning-Level System
   (GREEN / YELLOW / ORANGE / RED alert tiers)
                 │
                 ▼
             Step 4E
    Notebook 09 + Phase 4 Report
    Export inference API artifacts
```

---

## Step 4A — Conformal Prediction (Uncertainty Quantification)

**What:** Wrap XGBoost predictions in statistically valid coverage guarantees.

**Notebook:** `notebooks/09_conformal_prediction.ipynb`  
**Source module:** `src/conformal.py`

### Method
- Use the **validation set** (frozen from Phase 3) as the **CP calibration set**.
- Compute **nonconformity scores** from XGBoost predicted probabilities on the calibration set.
- At inference time, produce:
  - `flood_probability` — raw XGBoost score
  - `cp_lower` / `cp_upper` — conformal prediction interval at 90% coverage
  - `uncertainty_width` = `cp_upper − cp_lower` (wider = model less confident)
  - `cp_in_set` boolean flag (is the prediction set `{flood}` or `{no-flood}` or both?)

### Approach
- **Split Conformal Prediction** (most practical for tabular regression/classification):
  - Calibrate on the validation period (2023-01-04 → 2023-07-31, 6,199 rows).
  - Evaluate coverage on the test period.
- Target coverage levels: **80%, 90%, 95%**.
- Report empirical coverage vs nominal coverage — the key validity check.

### Deliverables
```
results/conformal/
├── calibration_scores.csv          # nonconformity scores on calibration set
├── cp_coverage_report.md           # empirical vs nominal coverage at 80/90/95%
├── cp_test_predictions.csv         # test-set predictions + intervals
└── cp_interval_width_analysis.csv  # interval width by district, season, rainfall level
```

### New source file: `src/conformal.py`
```
Functions:
  compute_nonconformity_scores(model, X_cal, y_cal) → scores
  get_conformal_threshold(scores, alpha) → qhat
  predict_with_intervals(model, X, qhat) → {prob, lower, upper, in_set}
  evaluate_coverage(predictions, y_true, alpha_levels) → coverage_df
```

---

## Step 4B — SHAP Interpretability

**What:** Explain *why* the model predicts a flood for each observation.

**Notebook:** `notebooks/09_conformal_prediction.ipynb` (same notebook, separate section)  
**Source module:** `src/explain.py`

### Global SHAP
- Compute SHAP values on the full test set using `shap.TreeExplainer` (XGBoost native).
- Plot:
  - **SHAP Summary Plot** (beeswarm): feature importance ranked by mean |SHAP|
  - **SHAP Bar Chart**: mean absolute SHAP per feature family (Rainfall, Discharge, Historical Flood, Landslide, Temporal, Spatial)
  - **SHAP Dependence Plots**: `rain_24h`, `discharge_anomaly`, `district_flood_severity_index`, `monsoon_phase`

### Local SHAP (per-prediction explanations)
- For every test-set prediction: store the SHAP value vector alongside the prediction.
- This becomes the per-location explanation displayed in the Phase 5 frontend.
- Export: `results/shap/test_shap_values.csv` (rows = test observations, cols = SHAP per feature)

### Deliverables
```
results/shap/
├── test_shap_values.csv            # full SHAP matrix for test set
├── shap_summary_plot.png           # global feature importance beeswarm
├── shap_bar_chart.png              # by feature family
├── shap_dependence_rain24h.png
├── shap_dependence_discharge.png
└── shap_mean_by_district.csv       # average |SHAP| per feature per district
```

### New source file: `src/explain.py`
```
Functions:
  compute_shap_values(model, X, feature_names) → shap_values_df
  plot_shap_summary(shap_df, feature_names, save_path)
  plot_shap_dependence(shap_df, X, feature, save_path)
  get_top_k_drivers(shap_row, k=3) → list[str]   # used by frontend
```

---

## Step 4C — Robustness Experiments (Observation Degradation)

**What:** Stress-test the model under realistic real-world sensor failure scenarios.

**Notebook:** `notebooks/10_robustness.ipynb`  
**Source module:** `src/robustness.py`

### Experiment Matrix

| Experiment | Description | Degradation Applied |
|:---|:---|:---|
| **R1 — Gaussian Noise** | Add increasing levels of Gaussian noise to rainfall features | σ = 5%, 10%, 20%, 50% of feature std |
| **R2 — Single Station Outage** | Zero-out / NaN-fill one rainfall station's features | Applied to each of 47 stations individually |
| **R3 — Discharge Sensor Failure** | Remove all `discharge_*` features (simulate gauge offline) | Drop 4 hydrology features |
| **R4 — Partial Feature Dropout** | Randomly mask 10%, 25%, 50% of features per row | Impute with training median |
| **R5 — Combined Degradation** | Noisy rainfall + discharge outage simultaneously | Realistic cascade failure scenario |

### Metrics per experiment
- ROC-AUC, PR-AUC, F1, Recall — how much does performance degrade?
- **Uncertainty width change** — does the CP interval widen under degraded input? (It should.)
- Flag observations where `uncertainty_width > threshold` → model signals its own unreliability.

### Deliverables
```
results/robustness/
├── robustness_summary.csv          # all experiments × all metrics
├── r1_noise_degradation.csv
├── r2_station_outage_results.csv
├── r3_discharge_outage.csv
├── r4_partial_dropout.csv
├── r5_combined_degradation.csv
├── robustness_report.md            # narrative summary
└── robustness_curves.png           # ROC-AUC vs. degradation level chart
```

### New source file: `src/robustness.py`
```
Functions:
  add_gaussian_noise(X, feature_cols, sigma_fraction)
  simulate_station_outage(X, station_id)
  simulate_feature_dropout(X, feature_cols, dropout_fraction)
  run_degradation_experiment(model, conformal_fn, X, y, degradation_fn) → metrics_dict
  run_all_experiments(model, X_test, y_test, experiment_configs) → results_df
```

---

## Step 4D — Operational Warning-Level System

**What:** Translate `flood_probability` + `uncertainty_width` into **4 operational alert tiers** that humans can act on.

**Notebook:** `notebooks/10_robustness.ipynb` (last section)  
**Source module:** `src/warning_levels.py`

### Alert Tier Design

| Tier | Label | Condition | Meaning |
|:---|:---:|:---|:---|
| 0 | 🟢 **CLEAR** | `prob < 0.15` | No significant risk. Normal monitoring. |
| 1 | 🟡 **WATCH** | `0.15 ≤ prob < 0.40` OR `uncertainty_width > 0.40` | Elevated attention. Monitor rainfall/discharge. |
| 2 | 🟠 **WARNING** | `0.40 ≤ prob < 0.70` | Significant risk. Prepare emergency teams. |
| 3 | 🔴 **ALERT** | `prob ≥ 0.70` | Imminent threat. Issue public warning, evacuate. |

- **Uncertainty modifier**: If `uncertainty_width > 0.35`, bump tier up by 1 (err on the side of caution).
- This tier assignment is **exported per test observation** and fed directly into the Phase 5 frontend.

### Deliverables
```
results/warning_levels/
├── test_warning_levels.csv         # all test rows with tier + probability + uncertainty
├── warning_level_confusion.csv     # tier vs actual event — false alarm / missed event analysis
├── warning_design_rationale.md     # justification of thresholds
└── warning_level_map_data.json     # GeoJSON-ready export for Phase 5 frontend
```

### New source file: `src/warning_levels.py`
```
Functions:
  assign_warning_tier(prob, uncertainty_width, thresholds) → int
  batch_assign_tiers(predictions_df, thresholds) → df with tier column
  export_map_geojson(predictions_df, stations_df) → GeoJSON dict
  false_alarm_analysis(tier_df, y_true) → confusion_df
```

---

## Step 4E — Phase 4 Report & Inference Export

**Notebook:** `notebooks/10_robustness.ipynb` (summary cells)

### Phase 4 Deliverables Report
```
results/
├── phase4_report.md                # full narrative of all Phase 4 experiments
└── inference_artifacts/
    ├── xgboost_model.joblib        # copy of frozen model (no retraining)
    ├── conformal_qhat_90.json      # CP threshold(s) for deployment
    ├── feature_columns.json        # exact feature list in the correct order
    ├── scaler_reference.json       # any normalization info (for future live data)
    ├── warning_thresholds.json     # tier boundary values
    └── shap_explainer.pkl          # serialized SHAP TreeExplainer
```

> [!IMPORTANT]
> The `inference_artifacts/` folder is the **single handoff package** to Phase 5.  
> Phase 5 loads these files directly — it never re-trains or re-calibrates anything.

---

## Phase 4 Notebooks Summary

| Notebook | Content |
|:---|:---|
| `09_conformal_prediction.ipynb` | CP calibration + interval construction + SHAP global/local + coverage validation |
| `10_robustness.ipynb` | All 5 degradation experiments + warning tier design + Phase 4 report + inference export |

---

## Phase 4 New Source Files

| File | Purpose |
|:---|:---|
| `src/conformal.py` | Nonconformity scores, prediction intervals, coverage evaluation |
| `src/explain.py` | SHAP computation, summary plots, local explanation extraction |
| `src/robustness.py` | Noise injection, outage simulation, dropout degradation experiments |
| `src/warning_levels.py` | Alert tier assignment, GeoJSON export, false-alarm analysis |

---

---

# Phase 5 — Frontend Dashboard: Interactive Flash-Flood Early Warning System

## Goal

A standalone, browser-based dashboard that:
- Shows a **live map of Uttarakhand** with all 47 rainfall stations and 7 river gauge stations plotted.
- Displays **flood risk warning levels** for each location using color-coded markers.
- On **hover or click** → shows a side panel with full prediction details, SHAP-driven explanations, and uncertainty bands.
- Loads directly from the `inference_artifacts/` and `results/warning_levels/` exports — **no backend server required** (pure static HTML/CSS/JS).

---

## Tech Stack

| Layer | Technology | Reason |
|:---|:---|:---|
| Structure | HTML5 | Native, no build step |
| Styling | Vanilla CSS | Full design control, glassmorphism |
| Logic | Vanilla JavaScript (ES6 modules) | Zero dependencies, runs anywhere |
| Map | **Leaflet.js** (CDN) | Lightweight, tile-based, offline-capable |
| Charts | **Chart.js** (CDN) | Probability gauges, timelines, bar charts |
| Data | Static JSON files from Phase 4 | Pre-computed — no live API needed |
| Fonts | Google Fonts — Inter + Space Grotesk | Premium typography |

> No React, no Node, no Flask. The entire dashboard is **a folder you can double-click and open in a browser**.

---

## Dashboard Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│  🌊  Uttarakhand Flash-Flood Early Warning System          [Header]  │
│  Last updated: Sep-14-2026 06:00 IST   |  Model: XGBoost + CP       │
├────────────────────────────────────┬─────────────────────────────────┤
│                                    │                                 │
│         LEAFLET MAP                │     LOCATION INSPECTOR          │
│                                    │     (appears on hover/click)    │
│   [Uttarakhand basemap]            │                                 │
│                                    │  📍 Rudraprayag District        │
│   ●  Station markers               │  Station: Rudraprayag (CWC)     │
│      color = warning tier          │  ──────────────────────         │
│      size = uncertainty width      │  🔴 ALERT — Prob: 0.83          │
│                                    │  Uncertainty: ±0.12             │
│   [District boundary overlays]     │                                 │
│   [River network lines]            │  ━━━━ Probability Gauge ━━━━   │
│   [Flood hotspot heatmap toggle]   │  [████████░░] 83%              │
│                                    │                                 │
│                                    │  📊 24h Rainfall Timeline      │
│                                    │  [Line chart — last 72h]        │
│                                    │                                 │
│                                    │  🔍 Top Risk Drivers (SHAP)    │
│                                    │  1. rain_24h        +0.41      │
│                                    │  2. monsoon_phase   +0.28      │
│                                    │  3. discharge_anom  +0.19      │
│                                    │                                 │
│                                    │  🟠 Uncertainty Band           │
│                                    │  [Shaded interval bar]         │
│                                    │  CP 90% interval: [0.71, 0.95] │
│                                    │                                 │
└────────────────────────────────────┴─────────────────────────────────┤
│  LEGEND: 🟢 CLEAR  🟡 WATCH  🟠 WARNING  🔴 ALERT  [Summary Stats] │
└──────────────────────────────────────────────────────────────────────┘
```

---

## File Structure (Phase 5)

```
frontend/
├── index.html                      # main dashboard page
├── css/
│   ├── main.css                    # global design system, tokens, dark mode
│   ├── map.css                     # map container and overlays
│   └── panel.css                   # inspector side panel styles
├── js/
│   ├── config.js                   # constants: map center, zoom, color palette
│   ├── data_loader.js              # fetch + parse static JSON data files
│   ├── map_renderer.js             # Leaflet markers, layers, district boundaries
│   ├── panel_renderer.js           # inspector panel build + update functions
│   ├── charts.js                   # Chart.js gauge, timeline, SHAP bar chart
│   ├── warning_colors.js           # tier → color/icon mapping
│   └── main.js                     # app entry point, wires everything together
├── data/
│   ├── stations.json               # 47 rainfall + 7 discharge stations with lat/lon
│   ├── warning_levels.json         # per-station: prob, tier, uncertainty, shap_drivers
│   ├── uttarakhand_districts.geojson  # district boundary polygons
│   ├── river_network.geojson       # major river lines (Ganga, Alaknanda, Mandakini…)
│   └── rainfall_timeseries.json    # last 72h hourly rainfall per station (for charts)
└── assets/
    ├── favicon.svg                 # flood drop icon
    └── alert_icons/                # SVG icons for each tier
        ├── clear.svg
        ├── watch.svg
        ├── warning.svg
        └── alert.svg
```

---

## Visual Design Spec

### Color System
```
Background:     #0a0e1a  (deep navy)
Surface:        #111827  (dark glass card)
Surface-border: rgba(255,255,255,0.08)
Accent:         #3b82f6  (electric blue — links, highlights)

Warning Tiers:
  CLEAR:    #22c55e  (green)
  WATCH:    #eab308  (amber)
  WARNING:  #f97316  (orange)
  ALERT:    #ef4444  (red)

Text-primary:   #f1f5f9
Text-muted:     #64748b
```

### Typography
- Headings: **Space Grotesk** (600–700 weight)
- Body + data: **Inter** (400–500 weight)
- Monospace: **JetBrains Mono** (probabilities, coordinates)

### Map Tiles
- Primary: **CartoDB Dark Matter** (matches dark theme perfectly)
- Fallback: OpenStreetMap

### Station Markers
- **Circle markers** with colored fill = warning tier
- **Radius** scales with `uncertainty_width` (more uncertain → larger, pulsing ring)
- **Pulsing animation** on ALERT-tier stations (CSS keyframe ring expansion)
- Hover → tooltip bubble with station name + probability
- Click → lock the inspector side panel open

### District Overlays
- Semi-transparent fill on hover: `rgba(tier_color, 0.15)`
- Outline stroke: `rgba(tier_color, 0.6)`
- Districts colored by **maximum tier** of any station within them

### Inspector Side Panel
- Glassmorphism card: `backdrop-filter: blur(12px)` + `background: rgba(17,24,39,0.85)`
- Slides in from the right with a smooth 250ms CSS transition
- Sections (expandable):
  1. **Header** — station name, district, coordinates
  2. **Warning Badge** — large colored tier badge + timestamp
  3. **Probability Gauge** — animated horizontal bar
  4. **Uncertainty Band** — shaded interval visualization
  5. **24h Rainfall Timeline** — Chart.js line chart (data from `rainfall_timeseries.json`)
  6. **River Discharge** — small sparkline (if discharge station nearby)
  7. **Top Risk Drivers (SHAP)** — horizontal bar chart (top 5 SHAP contributors)
  8. **Historical Context** — number of past flood events at this station

---

## Interactions

| Interaction | Behavior |
|:---|:---|
| Hover station marker | Show tooltip bubble + highlight district |
| Click station marker | Lock inspector panel open, deselect others |
| Click elsewhere on map | Close inspector panel |
| Click district polygon | Show district-level summary (all stations within) |
| Toggle "Heatmap" button | Show kernel-density flood risk heatmap layer |
| Toggle "River Network" | Show/hide river line overlays |
| Toggle "District Boundaries" | Show/hide district polygon outlines |
| Filter bar (top right) | Filter stations by tier: ALL / WATCH+ / WARNING+ / ALERT only |
| "How it works" button | Modal explaining CP, SHAP, XGBoost in plain language |

---

## Data Flow (Static JSON pipeline)

```
Phase 4 outputs
    │
    ├── results/warning_levels/warning_level_map_data.json
    │         ↓ (copy into frontend/data/)
    │   frontend/data/warning_levels.json
    │         ↓ (loaded by data_loader.js)
    │   map_renderer.js  →  Leaflet markers + district fills
    │   panel_renderer.js →  inspector content
    │   charts.js         →  gauges + SHAP bar chart
    │
    └── flash-flood-prediction/curated_dataset/cwc_rainfall_uttarakhand/
              ↓ (pre-processed by a one-time Python export script)
        frontend/data/rainfall_timeseries.json  →  24h timeline chart
```

> A single helper script `scripts/export_frontend_data.py` will:
> 1. Read Phase 4 `warning_level_map_data.json`
> 2. Read raw rainfall CSVs (last 72h)
> 3. Output all `frontend/data/*.json` files
> 
> This script runs **once** after Phase 4. The frontend itself is fully static thereafter.

---

## Phase 5 Notebooks / Scripts

| File | Purpose |
|:---|:---|
| `scripts/export_frontend_data.py` | One-time script: converts Phase 4 artifacts → `frontend/data/*.json` |
| `notebooks/11_frontend_data_export.ipynb` | Notebook version of the export script with validation cells |

---

## Phase 5 Build & Run

```powershell
# No npm, no build step. Just open the file:
start frontend/index.html

# Or serve it locally for cleaner file:// behavior:
py -m http.server 8080 --directory frontend/
# Then open: http://localhost:8080
```

---

## Phase 5 Definition of Done

- [ ] Map renders all 47 stations + 7 discharge stations on correct Uttarakhand coordinates.
- [ ] Station markers are correctly color-coded by warning tier.
- [ ] Marker size/pulse reflects uncertainty width.
- [ ] Hover shows tooltip with station name and probability.
- [ ] Click locks inspector panel with all 8 data sections populated.
- [ ] SHAP bar chart shows top-5 risk drivers with correct values.
- [ ] 24h rainfall timeline renders correctly for all stations.
- [ ] District polygons fill on hover/click.
- [ ] All 4 filter buttons work correctly.
- [ ] "How it works" modal explains the methodology.
- [ ] Full dark-mode, glassmorphism design renders correctly in Chrome and Firefox.
- [ ] No broken links, no missing data, no console errors.
- [ ] `scripts/export_frontend_data.py` produces all required JSON files from Phase 4 artifacts.

---

---

# Execution Order

```
TODAY ──────────────────────────────────────────────────────────► 
        
  Phase 4A           Phase 4B         Phase 4C         Phase 4D
  Conformal          SHAP             Robustness       Warning
  Prediction  ──►    Interpretability  Experiments ──►  Levels    ──►
  (nb 09)            (nb 09)          (nb 10)          (nb 10)
  ~1 hr              ~30 min          ~1-2 hr          ~30 min

          ↓
  Phase 4E
  Inference Export
  (inference_artifacts/)
  ~15 min

          ↓
  Phase 5A                Phase 5B              Phase 5C
  Data export             Core map +            Inspector panel
  script +    ──────►     station markers  ──►  + charts +       ──►  DONE ✅
  JSON prep               + layers              SHAP viz
  ~30 min                 ~2 hr                 ~2 hr
```

---

# Full Deliverables Checklist

## Phase 4

### Notebooks
- [ ] `notebooks/09_conformal_prediction.ipynb`
- [ ] `notebooks/10_robustness.ipynb`

### Source modules
- [ ] `src/conformal.py`
- [ ] `src/explain.py`
- [ ] `src/robustness.py`
- [ ] `src/warning_levels.py`

### Results
- [ ] `results/conformal/calibration_scores.csv`
- [ ] `results/conformal/cp_coverage_report.md`
- [ ] `results/conformal/cp_test_predictions.csv`
- [ ] `results/conformal/cp_interval_width_analysis.csv`
- [ ] `results/shap/test_shap_values.csv`
- [ ] `results/shap/shap_summary_plot.png`
- [ ] `results/shap/shap_bar_chart.png`
- [ ] `results/shap/shap_mean_by_district.csv`
- [ ] `results/robustness/robustness_summary.csv`
- [ ] `results/robustness/robustness_report.md`
- [ ] `results/robustness/robustness_curves.png`
- [ ] `results/warning_levels/test_warning_levels.csv`
- [ ] `results/warning_levels/warning_level_map_data.json`
- [ ] `results/warning_levels/warning_design_rationale.md`
- [ ] `results/phase4_report.md`

### Inference artifacts
- [ ] `results/inference_artifacts/xgboost_model.joblib`
- [ ] `results/inference_artifacts/conformal_qhat_90.json`
- [ ] `results/inference_artifacts/feature_columns.json`
- [ ] `results/inference_artifacts/warning_thresholds.json`
- [ ] `results/inference_artifacts/shap_explainer.pkl`

## Phase 5

### Scripts
- [ ] `scripts/export_frontend_data.py`
- [ ] `notebooks/11_frontend_data_export.ipynb`

### Frontend files
- [ ] `frontend/index.html`
- [ ] `frontend/css/main.css`
- [ ] `frontend/css/map.css`
- [ ] `frontend/css/panel.css`
- [ ] `frontend/js/config.js`
- [ ] `frontend/js/data_loader.js`
- [ ] `frontend/js/map_renderer.js`
- [ ] `frontend/js/panel_renderer.js`
- [ ] `frontend/js/charts.js`
- [ ] `frontend/js/warning_colors.js`
- [ ] `frontend/js/main.js`

### Data files (generated by export script)
- [ ] `frontend/data/stations.json`
- [ ] `frontend/data/warning_levels.json`
- [ ] `frontend/data/uttarakhand_districts.geojson`
- [ ] `frontend/data/river_network.geojson`
- [ ] `frontend/data/rainfall_timeseries.json`

### Assets
- [ ] `frontend/assets/favicon.svg`
- [ ] `frontend/assets/alert_icons/*.svg` (4 icons)
