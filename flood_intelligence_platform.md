# PRAHAR Master Brief: Multi-Source, Uncertainty-Aware Flash-Flood Intelligence for Uttarakhand

> **What this file is.** The single master brief ("master prompt") for the project. It is enough for a person or an AI assistant to understand PRAHAR, work on it, extend it or present it. It describes the product (what each feature does and its status), the as-built data and model, the rules that must not be broken, and where the detail lives.
>
> **Status legend:** ✅ built and verified · 🟡 partly built · ❌ planned (see `PRAHAR_MASTER_PLAN.md`).
>
> **Detail lives in:**
> - `PROJECT_DATA_GUIDE.md`: every dataset, model and metric
> - `PRAHAR_MASTER_PLAN.md`: the 240-task roadmap and the value audit
> - `docs/metrics.md`: metric definitions
> - `docs/architecture.md`, `docs/adr/`, `docs/ops/runbook.md`
> - `PRESENTATION_CHEATSHEET.md`: the numbers to say
> - `Data Science Course Project (1).md`: the original course brief (do not edit)
>
> **Project concept:** a multi-source, uncertainty-aware flash-flood early-warning platform for Uttarakhand. It predicts the chance of a flood in each district and at each rain gauge in the next 24 hours, says how sure it is and why, and translates the hazard into building and infrastructure exposure inside official river-setback zones.

---

## 0. Hard rules (read first)

1. **Course project only.** The hackathon "Track B / Space mode" work was moved to `../hackathon track-b/` and is not part of this project.
2. **Every number shown comes from the pipeline.** The UI reads exported JSON (`web/public/data/`) produced by `scripts/export_frontend_data.py`. Never hard-code a metric.
3. **Honest evaluation.** Adoption rules are fixed before an experiment runs. Results come with baselines and confidence intervals. Failed experiments are reported, not hidden.
4. **One definition per number** (`docs/metrics.md`):
   - The headline district-day CSI is the **strict** one: **0.095**.
   - The "flood today or tomorrow" version (0.169) is always labelled.
   - Lead time = the first sustained (≥ 3 h) switch-on to ALERT before the event day: **6/18 warned, median 3.5 h**.
5. **No leakage.** Features use the past only. Splits are chronological. Normalisation and calibration are fitted on train/calibration data only. Lat/lon are not model features.
6. **Decision support only.** No claims of damage, casualties, evacuation decisions, inundation depth or guaranteed arrival times.
7. **All constants live in `params.yaml`.** Change one only through a pre-registered rule; rerun the pipeline; tests and audit must stay green.
8. **Git: commits are authored and pushed only as `harshgitty58`.** No AI or tool attribution in commits or files. Local hooks enforce this. Push only to `github.com/harshgitty58/Flash_Flood_Prediction`.

---

## 1. Core product vision ✅

The system does not stop at "flood probability = 82 %". It answers the chain:

> **Will flooding happen? → When? → Where? → How sure are we? → What could be affected? → Why?**

```text
PREDICT → EXPLAIN → LOCATE → QUANTIFY EXPOSURE → SHOW UNCERTAINTY → VERIFY
```

**Users:**
- state and district disaster-management analysts (USDMA SEOC / DEOCs);
- hydromet forecasters;
- researchers and examiners;
- later, a simplified public / field view.

---

## 2. System architecture (as built) ✅

```text
                                 DATA SOURCES
 ┌─────────────┬──────────────┬───────────────┬───────────────┬──────────────┬──────────────┐
 │ CWC hourly  │ CWC river    │ IMD flood     │ GSI landslide │ District     │ ERA5 / DEM   │
 │ rain (44)   │ discharge(7) │ inventory(121)│ points (5,443)│ indices (13) │ (research)   │
 └──────┬──────┴──────┬───────┴───────┬───────┴───────┬───────┴──────┬───────┴──────┬───────┘
        └─────────────┴───────────────┴───────────────┴──────────────┴──────────────┘
                                         ↓
                CLEANING & QC (error code 511.5, cap 150 mm/h, quarantine, offline gauges)
                                         ↓
                HOURLY FEATURE TABLE (518,304 station-hours; 23 features; past-only)
                                         ↓
                XGBoost (LR, RF baselines) → Venn-Abers calibration → Mondrian conformal sets
                                         ↓
                HYBRID WARNING TIERS = max(ML tier, IMD rainfall tier) + trigger
                                         ↓
          ┌──────────────────────────────┼──────────────────────────────┐
          ↓                              ↓                              ↓
   WMO-style verification        SHAP explanations          IMPACT ENGINE: 575,339 buildings,
   (CIs, baselines, external)    (top-3 drivers)            roads, bridges, POIs × setback zones
                                         ↓
                    JSON export → FastAPI (/predict, /risk, /impact …) → React + MapLibre console
```

One command runs everything: `python scripts/run_all.py` (28 stages). Then `scripts/audit_pipeline.py` must report **0 fail, 0 warn**.

---

## 3. Key output categories

### 3.1 Flood probability ✅
- **What it is:** a calibrated probability (Venn-Abers) that a flood is recorded in the gauge's district today or tomorrow.
- **How to read it:** it is read against the base rate (about 4–6 %), not as a 0–100 % "risk score".
- **Known issue:** the model emits only about 109 distinct scores, so probabilities look stepped (V-02). The fix is planned.

### 3.2 Warning tiers (severity of the warning) ✅
`NORMAL · WATCH · ALERT · SEVERE · EXTREME`, mapped to IMD colours Green · Yellow · Orange · Red · Red + "extreme".

**ML layer.** Calibrated probability against multiples of the base rate (0.0426):

| Tier | Multiple | Cut-off |
|---|---|---|
| WATCH | 2× | 0.085 |
| ALERT | 5× | 0.213 |
| SEVERE | 10× | 0.426 |
| EXTREME | 20× | 0.852 |

A conformal FLOOD-only 90 % set lifts the tier to at least ALERT.

**Rainfall layer (IMD 24 h categories):**

| IMD category | 24 h rain | Tier |
|---|---|---|
| moderate | 15.6 mm | WATCH |
| heavy | 64.5 mm | ALERT |
| very heavy | 115.6 mm | SEVERE |
| extremely heavy | 204.5 mm, or a cloudburst ≥ 100 mm in 1 h | EXTREME |

Susceptibility shifts the rain tier by ±1 level (landslide hotspot and flood-prone district).

**Final tier** = the higher of the two. The `trigger` (ml / rainfall) is always shown.

Flood *severity* (deaths, damage classes) is a planned secondary target ❌.

### 3.3 Lead time 🟡
- **Measured:** 6 of 18 floods warned before the event day, median **3.5 h** (strict definition).
- It is a nowcast: there are no weather-forecast inputs yet.
- No "expected peak at 15:20" style claims until forecast inputs exist ❌.

### 3.4 Confidence / uncertainty ✅
- Each prediction carries: Venn-Abers interval, conformal p-values, **confidence** and **credibility**, and a **90 % set** ({FLOOD} / {NO FLOOD} / UNCERTAIN).
- Coverage on the held-out month: every flood hour fell inside the 90 % set.
- **Planned:** plain-language confidence classes (High / Medium / Low) that explain *why*, for example "2 of 4 gauges offline" ❌.

### 3.5 Multi-source agreement 🟡
- **Built:** source-health card (gauges reporting n/N, discharge readings, static sources).
- **Research features exist** (Exp H): gauge-vs-ERA5 rain ratio, "both wet" flag.
- **Planned:** a per-station agreement score once satellite rain (IMERG, already downloaded) is in the model ❌.

### 3.6 Missing-data impact ✅
These numbers are measured from real inference-time degradation, not hard-coded (`results/robustness/`):

| Scenario | ROC-AUC | Change |
|---|---|---|
| Baseline | 0.716 | — |
| Rain noise 20 % | 0.712 | −0.004 |
| Discharge offline | 0.716 | 0.000 |
| 25 % of inputs dropped | 0.647 | −0.069 |
| **Flood history missing** | **0.500** | **−0.216** |

Shown on the Uncertainty page. **Finding:** the model leans on district history (prior dominance).

### 3.7 Explainable prediction ✅
- **Per prediction:** the top 3 SHAP drivers, in the station drawer.
- **Global importance:** flood history 66 %, rainfall 24 %, landslide 10 %, discharge 0 %.
- **Wording:** "contribution / importance", never causation.

---

## 4. Building-level exposure module ✅

### 4.1 Goal
Translate the hazard tier at each gauge (or a district estimate where no gauge reports) into building and infrastructure exposure, within the **legal frame of official river-setback zones**.

```text
Hazard tier per centre (5 km radius) → distance of each building to the nearest mapped river
→ official zone A/B/C → exposure class (+ height above river shown for information)
```

### 4.2 Building footprints ✅
- **Microsoft Global ML Building Footprints:** polygons extracted from imagery by a pretrained deep segmentation model. **575,339 buildings** are scored.
- **OSM via Overpass:** rivers and streams, roads, bridges, schools, hospitals, place names.
- **Not used:** a home-trained building detector. It's optional, and existing footprints are more reliable.

---

## 5. Exposure calculation (as built) ✅

| Zone | Distance from river | Legal basis | Class |
|---|---|---|---|
| A | ≤ 50 m | NGT order, Dec 2017 | = hazard tier |
| B | 50–100 m | NGT; Jal Shakti Flood Plain Zoning guidelines 2025 | one level lower |
| C | 100–200 m | Uttarakhand High Court, Aug 2013 | two levels lower |
| — | beyond 200 m | — | MINIMAL |

- **Classes:** MINIMAL · LOW · MODERATE · HIGH · CRITICAL (score bands 0–20 / 20–40 / 40–60 / 60–80 / 80–100).
- **Audit:** `scripts/audit_impact.py` finds **0 zone and 0 class mismatches** across all buildings.
- **Not computed:** water depth, inundated footprint %, duration. The legal flood plain is the 1-in-100-year highest flood level + 1 m, and those maps are not public. Height above river is information only.
- **Planned** ❌: real HAND from the 30 m DEM (the code exists: `src/terrain.py`); a probability-aware risk score beside the legal class; population exposure; lake and canal distances.

### 5.1 Building card (as built) ✅
Click a building to see: zone, distance to river, height above river, the hazard tier of its centre, the source of the hazard (live gauge / last report / district estimate), and the class.

---

## 6. Infrastructure exposure 🟡
- **Built:** 1,327 road segments, 228 bridges, schools and hospitals near water, and 13,752 named places and landmarks are listed and searchable. OSM gaps are stated ("0 schools mapped" means OSM is missing them, not that there are none).
- **Planned** ❌: roads coloured by exposure, and population counts.
- **Always described as exposure estimates**, never emergency decisions.

---

## 7. Risk priority 🟡
- **Built:** "Districts to watch", a daily ranking from the district-day model. Recall@3 on external events is 0.345, against a prior of 0.207 and chance of 0.231.
- **Planned** ❌: a transparent ranking by (tier, exposed population, critical facilities in zones A/B, bridges at risk).
- **Known flag:** the "top 3 = ALERT" rule fires even on dry days. The fix is to use an absolute probability cut-off.

---

## 8. User interface ✅

**Navigation** (PRAHAR console, `/app/*`): Overview · Forecast · Risk Map · Impact · Uncertainty · Events · Data & Model · Metrics · System, plus the Landing page `/`.

**Persistent header:** replay time (currently 12 Sep 2024 19:00), gauges reporting (27/44), model version, and data-source health.

**Visual language:**
- dark-forest glass UI;
- tier colours as tokens (NORMAL #3ddc97, WATCH #f5d547, ALERT #ff9f1c, SEVERE #ff4d2e, EXTREME #e0115f);
- a river-landscape page transition: a flat card in which the river widens toward the viewer.

**Modes:**
- **static:** reads `web/public/data`; used for Vercel;
- **API:** the Vite proxy `/api` to FastAPI.

---

## 9. Landing ✅ and Overview ✅
- **Landing:**
  - hero with Sentinel-2 landscapes and 2013 flood photographs;
  - live replay card (top station, tier, trigger, stations ≥ SEVERE);
  - "One question leads to the next";
  - "Three intelligence layers": Hazard · Uncertainty · Exposure;
  - **Verified results** (CSI 0.095 vs baselines, 7/21 external, BSS 0.073, 6/18 warned);
  - numbers band and disclaimer.
- **Overview:**
  - peak-station tier with its **trigger** (for example "EXTREME · 141 mm · set by rainfall · ML 2 %");
  - ≥ SEVERE count, reporting share, conformal confidence, exposed buildings;
  - regional risk trajectory, global drivers (SHAP by group), "Districts to watch", data sources.

## 10. Forecast 🟡
- **Built:** probability over the replay window with a station-spread band; peak in the next 24 h; the lead-time result card.
- **Planned** ❌: a conformal band per hour, horizons of 6 / 12 / 24 h, observed rain bars.

## 11. Risk Map ✅
- **Built:**
  - MapLibre, with Dark / Satellite / Terrain basemaps and 3-D terrain;
  - stations coloured by tier;
  - the **station drawer**: calibrated p, confidence, credibility, 90 % set, ML vs rain tier, trigger, top-3 SHAP drivers;
  - place search with auto-zoom, and hover coordinates.
- **Planned** ❌: a time scrubber, an IMERG rain overlay, catchment layers, and "what rain would make this ALERT".

## 12. Impact ✅
- **Built:** building outlines by class (quadtree tiles, about 0.74 MB per view), landmarks, bridges and roads lists, an object card, and place search (towns, villages, gauges).
- **Planned** ❌: PMTiles, a probability-aware score alongside the legal class, population, a critical-facility filter, exports.

## 13. Uncertainty ✅
- **Built:** source health, the **fusion ablation** (event-CV ROC per experiment: rain only 0.50 → + flood history 0.77), conformal coverage at 80 / 90 / 95 %, and the inference-time degradation table.
- **Planned** ❌: a reliability diagram, coverage by stratum, coverage under degradation.

## 14. Events 🟡
- **Built:** the IMD event list (121) and recent events. External validation with source links appears on Metrics.
- **Planned** ❌: **event replay** (T−72 h → T+24 h animation with hit / miss / false alarm and lead time).

## 15. Data & Model ✅ (+ Metrics ✅, System ✅)
- **Data & Model:** model comparison (validation vs test), SHAP importance, leave-one-event-out table, coverage by month, normalisation parameters.
- **Metrics:**
  - hour-level table with **base rate and PR-AUC lift**, a threshold slider (exploration only), the confusion matrix;
  - layer contribution and event-level table;
  - **WMO-style verification** (POD / FAR / CSI / ETS / HSS with 95 % CIs; baselines: climatology, persistence, district prior, rain rule);
  - BSS / ECE, honest lead time, relative economic value;
  - external validation (29 events, sources), and the ground-truth / label-audit panel.
- **System:** external services up/down, API status, measured latency (p50 / p95).

## 16. Mobile / field view ❌
Planned: a `/field` PWA showing "my location → nearest gauge, district tier, bulletin, offline cache", in English and Hindi. The desktop console is responsive meanwhile.

## 17. Cross-page flow (demo journey) ✅

```text
LANDING (verified results) → OVERVIEW ("EXTREME at Haldwani, 141 mm, set by rainfall; ML says 2 %")
→ RISK MAP (Pithoragarh: rain SEVERE vs ML NORMAL; 90 % set UNCERTAIN; SHAP drivers)
→ IMPACT (Haldwani: buildings by setback zone; click one)
→ UNCERTAINTY (fusion ablation; what fails if a source drops)
→ METRICS (CSI 0.095 vs baselines 0.036 / 0.053; external 7/21 with sources)
→ close on limits
```

Story: **Predict → Explain → Locate → Quantify exposure → Show uncertainty → Verify**.

## 18. Counterfactual sensor reliability ✅
Built as the inference-time degradation table (§3.6). The API also offers `POST /predict/scenario` (what-if overrides, for example `rain_24h = 120`).

## 19. Area exposure summary 🟡
Per-centre counts by class exist in `impact.json` (`by_station`, `by_class`). A zone summary card is planned ❌.

## 20. "Why is this area risky?" ✅
The station drawer shows the SHAP top-3, the ML vs rainfall tier and the trigger. Source agreement is planned (§3.5).

## 21. Zone comparison ❌
Planned: compare two zones by hazard against exposure.

---

## 22. Technical stack (as built)

| Layer | Stack |
|---|---|
| Data / ML | Python 3.12, pandas 2.3, NumPy, scikit-learn 1.7, **XGBoost 3.2**, SHAP 0.51, SciPy, rasterio (DEM), PyYAML |
| Uncertainty | own Venn-Abers + Mondrian conformal (`src/conformal.py`) |
| Geo | Shapely 2 (STRtree), MS footprints, OSM Overpass, AWS Terrarium tiles, Copernicus GLO-30, `src/terrain.py` (D8, HAND, TWI, SPI) |
| Backend | FastAPI + Uvicorn; ETag/304 blobs; O(1) online features; CORS allow-list; token-protected admin |
| Frontend | React 19, Vite 8, TypeScript, Tailwind 4, MapLibre GL 6, Recharts 3 |
| Quality | pytest (51 tests), audit script, GitHub Actions CI |
| Hosting | Vercel (web, static mode), Render free tier (API, 335 MB RAM) |
| Planned | PostgreSQL + PostGIS, MLflow, Prefect, PMTiles (`PRAHAR_MASTER_PLAN.md` §5) |

**Model policy:** use the simplest model that works for the data. No deep learning for show; about 50 training flood-days can't support it.

---

## 23. ML output contract (as built: `POST /predict`, snapshot rows)

```json
{
  "station": "Haldwani_1",
  "time": "2024-09-12T19:00:00",
  "p": 0.0182,                    // calibrated probability (Venn-Abers)
  "raw_score": 0.1835,            // XGBoost raw score
  "confidence": 0.668, "credibility": 0.634,
  "cp_set_90": "UNCERTAIN",       // FLOOD | NO_FLOOD | UNCERTAIN
  "tier": "EXTREME", "tier_ml": "NORMAL", "tier_rain": "EXTREME", "trigger": "rainfall",
  "signals": { "rain_24h": 140.5, "rain_1h": 0.0 },
  "drivers": [ { "feature": "district_flood_severity_index", "shap": -0.84, "value": 1.15 } ],
  "latency_ms": 15.1
}
```

Planned additions ❌: `confidence_class`, `data_health`, `valid_from` / `valid_to`, `model_version`, PREPARE district outlook.

## 24. Impact output contract (as built: building tiles `web/public/data/bld/{z}/{x}/{y}.json`)

Each building is a GeoJSON polygon with compact properties (kept small for fast map tiles):

```json
{ "i": 1, "st": 6, "src": 0, "z": 3, "s": 5, "h": 112, "d": 809, "a": 163 }
```

| Key | Meaning |
|---|---|
| `i` | building id within the export |
| `st` | index of the hazard centre (gauge or district-estimate town) in `impact.json` |
| `src` | hazard source: 0 live gauge · 1 last report ≤ 7 days · 2 district estimate |
| `z` | setback zone: 0 = A ≤ 50 m · 1 = B 50–100 m · 2 = C 100–200 m · 3 = outside |
| `s` | exposure score (class bands: MINIMAL < 20 ≤ LOW < 40 ≤ MODERATE < 60 ≤ HIGH < 80 ≤ CRITICAL) |
| `h` | height above the nearest river (m, information only) |
| `d` | distance to the nearest mapped river or stream (m) |
| `a` | footprint area (m²) |

Summary keys: `buildings_in_radius`, `buildings_exposed`, `by_class`, `by_station`, `by_source`, `roads`, `bridges`, `schools`, `health`, `coverage`.

---

## 25. What NOT to claim ✅ (enforced in UI copy and docs)
- **Never claim:**
  - structural damage, monetary loss, casualties, or evacuation decisions;
  - inundation depth or extent (this is an exposure proxy);
  - guaranteed arrival times or lead times beyond the measured 3.5 h median;
  - "accuracy %" as the headline (use PR-AUC with base rate, CSI / POD / FAR, BSS);
  - causation from SHAP.
- **Use:** predicted, estimated, potentially exposed, model confidence, decision support.
- **Disclaimer on every page:** "Decision-support prototype; follow IMD / USDMA / district advisories."

---

## 26. Scope delivered for the course (replaces "MVP for a hackathon")

| Course objective | Delivered |
|---|---|
| 1. Multi-source curation | ✅ CWC rain + discharge, IMD floods, GSI landslides, district indices, ERA5, DEM; 96-event multi-source label set; IMERG 2001–2025 downloaded |
| 2. Cleaning, normalisation, features | ✅ QC rules with tests; 5 silent bugs fixed; 23 past-only features; parameterised normalisation; O(1) online features |
| 3. Multi-model training and evaluation | ✅ LR / RF / XGBoost; time-series tuning; chronological + leave-one-event-out; fusion ablation A–T |
| 4. Uncertainty and robustness | ✅ Venn-Abers + Mondrian conformal; sensor-failure suite; hybrid warning tiers; WMO verification; external validation |
| Product | ✅ 10-page console, building-level exposure, FastAPI, CI, docs |

## 27. Next differentiators (v1.0) ❌
- **District-day "PREPARE" model:** trained on 2001–2025 gridded data (IMERG, ERA5 / ERA5-Land, GloFAS).
- **Labels and features:** labels back-filled to 2001; the 30 m terrain suite; soil moisture, runoff, CAPE.
- **Model:**
  - a finer XGBoost with Platt / beta calibration (both passed the pre-set rule in `results/v3/rq4_calibration.md`);
  - fixes to the alert logic: no ML alert without rain, district estimates by probability, lake-side exposure.
- **Product:** time scrubber, event replay, alerts and sitrep PDF, database mode.

## 28. Showcase features (later) ❌
Zone comparison, the mobile `/field` PWA, Hindi UI, a CAP alert feed (status "Exercise"), and Himachal Pradesh / Sikkim transfer.

## 29. Demo sequence (3 minutes) ✅
1. **Landing.** Verified results: "CSI 0.095, 2–3× the baselines; 7 of 21 later floods caught."
2. **Overview.** "EXTREME at Haldwani: 141 mm in 24 h, set by the IMD rule; the ML layer says 2 %. We show both."
3. **Risk Map → Pithoragarh.** "Rain says SEVERE, ML says NORMAL, and the 90 % set says UNCERTAIN. Here's why (SHAP)."
4. **Impact → Haldwani.** "Buildings within 50 / 100 / 200 m of the river, by the official NGT / Jal Shakti / High Court zones."
5. **Uncertainty.** "Rain at the gauge alone is no better than chance; flood history matters most; here's what fails if a sensor drops."
6. **Metrics.** "WMO-style scores with confidence intervals against baselines; external events with sources."
7. **Close.** The five data bugs we found and the honest limits.

## 30. Final product definition

> **PRAHAR is an uncertainty-aware, multi-source flash-flood early-warning platform for Uttarakhand. It fuses gauge rainfall, river discharge and flood/landslide history into calibrated 24-hour flood probabilities, combines them with IMD rainfall rules into explainable warning tiers with conformal confidence, and translates them into building-level exposure inside official river-setback zones, verified honestly against baselines and independent events.**

**Three intelligence layers:**

| Layer | Question | How |
|---|---|---|
| **1. Hazard** | will a flood happen? | calibrated XGBoost + IMD rainfall rule |
| **2. Uncertainty** | how sure are we? | conformal sets, source health, robustness |
| **3. Exposure** | what could be affected? | buildings, roads, bridges, POIs × setback zones |

**One-line pitch:** *"From 'flood probability = 82 %' to 'this district, this rainfall, these buildings along this river, with this much confidence, verified against real floods'."*

## 31. Design principles ✅
1. Map-first, not chart-first.
2. Every prediction carries uncertainty.
3. Every risk is spatially explorable.
4. Every number is traceable to a source file.
5. No ML jargon in the main flow; details on click (progressive disclosure).
6. Desktop for analysis; mobile for field awareness (planned).
7. Prototype scores are never presented as validated damage predictions.
8. Never hard-code metrics.
9. Show the trigger: users must know whether rain or the model raised an alert.
10. One memorable end-to-end story.

## 32. The core "wow"
The moment the demo moves from a district warning ("EXTREME, 141 mm, set by rainfall") to **specific buildings along a specific river inside the legal 50 m zone**, while the confidence and the verification stay visible. That's where PRAHAR becomes a complete, honest flood-intelligence platform rather than another flood model.

---

## Appendix A: As-built facts sheet (quote these)

| Item | Value | Source |
|---|---|---|
| Station-hours / labelled / flood hours | 518,304 / 126,904 / 1,951 | `web/public/data/model.json` |
| Gauges / districts | 44 rain + 7 river / 13 | same |
| Splits | train < 2023-07-01 (94,154 rows, 367 floods) · val Jul 2023 (20,280, 864) · test 1–25 Aug 2023 (12,469, 720) | `results/splits.json` |
| Deployed model | XGBoost, 23 features (Exp G); 100 trees, depth 5, lr 0.01, scale_pos_weight 255.55 | `models/xgboost/metadata.json` |
| Test hour level (XGBoost) | ROC-AUC 0.708 · PR-AUC 0.150 (base 0.058, 2.6×) · F1 0.320 · MCC 0.295 | `results/metrics/metrics_summary.csv` |
| Leave-one-event-out (deployed) | ROC-AUC 0.701 · PR-AUC 0.186 (base 0.081) | `results/event_cv/event_cv_summary.csv` |
| Hybrid ≥ ALERT, station-hour test | precision 0.234 · recall 0.650 | `results/warning_levels/warning_thresholds.json` |
| District-day CSI, strict (test) | **0.095** [0.034–0.165], POD 0.70, FAR 0.90; prior 0.036, persistence 0.053 | `results/verification/verification.json` |
| BSS / ECE | 0.073 / 0.012 | same |
| Honest lead time | 6 / 18 warned before the event day, median 3.5 h | same |
| External validation | 7 / 21 (POD 0.33 [0.14–0.52]), events 2023-09 → 2025-09 | `results/metrics/external_validation.json` |
| Conformal 90 % | coverage 0.884; flood hours 1.00; 85 % uncertain | `results/conformal/cp_summary.json` |
| Labels | 96 events / 130 district-days (2022–25), 5 source families | `data/external/labels/labels_summary.json` |
| Impact | 575,339 buildings; 0 zone / class mismatches; 1,327 roads; 228 bridges; 13,752 places | `scripts/audit_impact.py`, `impact.json` |
| Latency | `/predict` 17 ms p95; tile 0.74 MB / 175 ms; API RAM 335 MB | `results/latency/benchmarks.csv` |
| Quality | 51 tests; audit 0 fail; CI green | `tests/`, `.github/workflows/ci.yml` |

## Appendix B: Repository map

| Path | What |
|---|---|
| `params.yaml` | all constants (QC, features, tiers, rain rule, impact, API) |
| `curated_dataset/` (+ `MANIFEST.sha256`) | raw sources, pinned |
| `src/` | pipeline, features, target, training, event CV, conformal, tiers, verification, labels, district-day, studies, terrain |
| `scripts/` | `run_all.py`, export, impact layer, tiles, labels, fetchers (IMERG, CDS), audits, benchmarks |
| `backend/` | FastAPI app + inference engine |
| `web/` | React console |
| `results/` | every metric and report; `results/v3/` = v1.0 studies |
| `docs/` | architecture, metrics, licences, ADRs, runbook |
| `tests/` | data, labels, online features, terrain, model behaviour, API and security |
