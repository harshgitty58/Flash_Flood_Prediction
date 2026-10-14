# PRAHAR — Execution Plan (data → models → APIs → latency → frontend)

Written 2026-10-11. Supersedes the ordering in `REMAINING_TASKS.md` for the next working block.

## ✅ Status — 2026-10-11 (end of execution block)

| Phase | Result |
|---|---|
| **D — data** | 3 more data bugs fixed: offline gauges were filled as "0 mm dry" (58 % of the grid), labels sat on the day *before* each flood, same-day leakage in history features. 518,304 real station-hours; Window A train/val/test = 94,154 / 20,280 / 12,469 rows (271 / 384 / 240 flood hours). Normalisation params saved (`results/preprocessing/normalization_params.json`). **12 data tests green.** |
| **D2 — labels 2024-25** | 12 documented disasters curated with sources (`supplement_2024_2025.csv`), used as **external validation** (not training): hybrid warned for **4/8** events with gauge data (ML alone 2/8, rainfall alone 3/8), up to 48 h ahead; 4 events had no reporting gauge. |
| **M — notebooks 09-14** | All 6 batches executed headless, outputs saved in the `.ipynb`, timings in `results/notebook_runs.csv`. |
| **Accuracy** | Leave-one-event-out (primary): deployed XGBoost (Exp G) ROC-AUC **0.86**, PR-AUC 0.20 (4× base), **5/11 floods detected, median lead 48 h**. Single-month chronological test is weak for every model (XGB ROC 0.53, F1 0.08; RF F1 0.14). Hybrid ≥ ALERT on test: precision 0.12, **recall 0.47**, F1 0.19 (ML alone recall 0.28). Calibration: Brier 0.068 → 0.019; 90 % conformal sets cover 94 % (floods 88 %). Full table: `results/metrics/metrics_summary.csv`. |
| **M5 — hybrid tiers** | final = max(ML tier at 2/5/10/20× base rate, IMD rainfall tier ± susceptibility); trigger recorded per station. |
| **A — APIs** | FastAPI backend (`backend/app.py`): 14 endpoints incl. `/predict`, `/predict/scenario`, `/health/external`; ETag/304 + gzip; frontend switches with `npm run dev:api`. **29 tests green** (data + online features + API). External services 9/10 up (one Overpass mirror down; main Overpass + retry/backoff cover it). |
| **L — latency (measured)** | buildings per view 22.8 MB → ≤ 0.7 MB tile (104 KB gzipped, 86 ms); features per station-hour 1.3 ms → **0.2 ms** (O(1), identical to batch); calibration per score 4.3 ms → **0.007 ms** (lookup table); `/predict` p50 14 ms; data endpoints ~1 ms (0.5 ms on 304); impact rebuild 25+ min (never finished) → **~1 min** (vectorised). |
| **F — frontend** | New **Metrics** (per-model table, confusion matrix, threshold slider, warning-layer comparison, event + external-validation tables) and **System** (service health, API, latency, notebook batches) pages; tile-based buildings; hybrid trigger in drawer and hero; coverage heatmap + normalisation table on Data & Model; strict-JSON export. |
| **V — verify** | `run_all.py` export → audit: **audit 0 fail**, all pages screenshot-checked against the live API, no page/API errors. |

**Still open:** labels for 2023-09 → 2025-12 are too sparse to train on (news covers only major events) · rainfall layer over-alerts in July 2023 (validation precision 0.01) · headless (no-GPU) rendering of ~45k polygons is slow; fine on GPU browsers · `days-since-flood`-style features need fresh labels before they can return.

Principle: **data is the key**. Nothing is trained, exported or shown until the data stage passes its tests.

---

## 0. Where we stand (verified, not assumed)

### 0.1 What each dataset actually covers
| Source | Valid coverage | Notes |
|---|---|---|
| CWC rainfall (hourly) | 2022-01-31 → 2026-09-14 | 18 stations in 2022, 39–41 in 2023–25, 36 in 2026; only rainy hours are logged |
| CWC river discharge | 2022-08 (1 gauge) / **2023-06 → 2025-12** (7 gauges) | Tekhla starts 2024-03, Kheri ends 2024-08 |
| IMD flood inventory (labels) | 1970 → **2023-08-26** | 2021: 14, 2022: 7, 2023: 22 district-events; date only, no time |
| GSI landslides, district indices | static | |

**Where the datasets meet:**
| Window | Rain | Discharge | Labels | Verdict |
|---|---|---|---|---|
| A. 2022-02-01 → 2023-08-25 | ✓ | partial (mostly NaN) | ✓ | **Usable training window today** (19 months, 2 monsoons, 29 district-events) |
| B. 2023-06-07 → 2023-08-25 | ✓ | ✓ | ✓ | All three meet, but only 11 weeks / 1 monsoon: too short to train on alone |
| C. 2023-06-07 → 2025-12-31 | ✓ | ✓ | ✗ (labels stop 2023-08) | Best overlap of sensors, **needs curated labels (step D2)** |

→ Default: train/validate on **Window A**, treat discharge as missing-aware, use 2023-08-26 → 2026-09-14 for replay/inference only.
→ If labels for 2023-09 → 2025-12 are curated (D2), switch to **Window C**, where every modality overlaps.

### 0.2 Bugs already fixed in the data stage (this week)
timestamp parsing (47 % rows lost) · row-based rolling windows on sparse data · sentinel 511.5 / >150 mm/h / faulty gauges (Yamuna Colony, Roorkee_2, Purola_1) · duplicate station-hours · labels on the wrong day (flood-day rain labelled 0) · same-day leakage in history features · drifting history counters (removed from final model).

### 0.3 Open problems
1. Rainfall alone has no skill against IMD district-date labels (event-CV ROC 0.49) → the map rarely goes red even in real cloudbursts (31 Jul 2024, 5 Aug 2025).
2. Impact stage failed on a network drop (no retry); 8.7 MB GeoJSON makes map load slow.
3. No backend: the web app reads static JSON; external services (tiles, Overpass, footprints) are not health-checked.
4. Phase 4 has scripts but no notebooks; Jupyter is not installed.

---

## Phase D — Data first (gate: `pytest tests/test_data.py` all green)

| # | Step | Output |
|---|---|---|
| D1 | **Coverage analysis** per source/station/month; choose window (A now, C after D2) via `src/config.py: STUDY_START/STUDY_END` | `results/data_audit/coverage_matrix.csv` + heatmap |
| D2 | *(needs your OK)* **Curate labels 2023-09 → 2025-12** from NDMA/SDMA/IMD reports with source URLs per event | `curated_dataset/flood_inventory/supplement_2023_2025.csv` |
| D3 | **Normalisation with saved parameters**, fitted on the training window only: rainfall/discharge → `log1p` then robust scaling (median/IQR); counts/indices → z-score; flags untouched | `results/preprocessing/normalization_params.json` (per-feature method, centre, scale, fit window) |
| D4 | **Data tests** (pytest): parse rate = 100 %, hourly grid gap = 1 h, no duplicates, no valid rain > 150 mm/h, label coverage ends ≤ inventory end, no feature uses future rows, normalisation params reproduce on reload | `tests/test_data.py` |
| D5 | Train / val / test partition recorded once in `results/splits.json` and reused by every notebook | |

## Phase M — Training in Jupyter, in precise batches (gate: metrics table complete)

Install `jupyter nbconvert ipykernel`; each notebook is executed headless (`jupyter nbconvert --execute`) so outputs are saved in the `.ipynb`.

| Batch | Notebook | Does | Saves |
|---|---|---|---|
| M1 | `09_data_window_and_normalization.ipynb` | D1 + D3 + D5, plots of coverage and scaled distributions | params, splits |
| M2 | `10_retrain_models.ipynb` | LR / RF / XGBoost on the window, fixed seeds, tuned on val | models + `model_registry.csv` (one row per run) |
| M3 | `11_event_validation.ipynb` | leave-one-event-out CV, lead time | `results/event_cv/*` |
| M4 | `12_uncertainty_calibration.ipynb` | Venn-Abers + conformal, coverage | `results/conformal/*` |
| M5 | `13_warning_levels_hybrid.ipynb` | ML tiers + *(needs your OK)* **rainfall-threshold layer** (IMD heavy 64.5 / very heavy 115.6 / extreme 204.5 mm·24h⁻¹, cloudburst 100 mm·h⁻¹, scaled by district susceptibility); final tier = max(ML, rainfall) | `results/warning_levels/*` |
| M6 | `14_explainability_robustness.ipynb` | SHAP + sensor-failure scenarios | `results/shap/*`, `results/robustness/*` |

**Metrics reported for every model and both levels (hour and event):**
precision · recall · F1 · specificity · balanced accuracy · MCC · ROC-AUC · PR-AUC · Brier · confusion matrix at the frozen threshold · events detected · median lead time · false alarms per station-month. One table: `results/metrics/metrics_summary.csv`.

## Phase A — APIs: build them and prove they are connected (gate: `pytest tests/test_api.py` + health page green)

**A1 Backend (FastAPI)** replacing static JSON 1-for-1 (frontend switches by base URL):
`/health` · `/stations` · `/risk/snapshot?at=` · `/risk/timeline` · `/model/summary` · `/metrics` · `/events` · `/impact/summary` · `/impact/tiles/{z}/{x}/{y}` · `/landmarks?bbox=` · `POST /predict` · `POST /predict/scenario`.

**A2 External API health check** (`scripts/check_apis.py`, also exposed as `/health/external`): CARTO style + glyphs, Esri imagery + labels, AWS Terrarium DEM, OpenTopoMap, Overpass (3 mirrors), Microsoft footprints index, Google Fonts — status, latency, last success.

**A3 Resilience**: retry with exponential backoff + mirror fallback on every download (the impact stage died on a DNS error), cache-first for anything already fetched.

## Phase L — Latency (target budgets)

| Path | Today | Algorithm | Target |
|---|---|---|---|
| Map first paint (buildings) | 8.7 MB GeoJSON in one fetch | **Quadkey tiling (z12) + level-of-detail**: buildings pre-cut into tiles, client loads only tiles in view; below z12 a pre-aggregated count per tile | < 300 KB per view, < 1 s |
| Data fetch | uncompressed JSON | gzip/brotli, `Cache-Control` + ETag, parallel prefetch of next page's data | p95 < 200 ms (so the river loader rarely appears) |
| Feature computation for live inference | recompute all windows | **Incremental O(1) state per station**: ring buffer for 3/6/12/24/48/72 h sums + running max (monotonic deque) + recursive API (API_t = 0.85·API_{t-1} + P_t) | < 1 ms / station / hour |
| Model + uncertainty | Venn-Abers isotonic fits | model loaded once; **precomputed calibration lookup** (grid → `np.interp`) + conformal p-values by `searchsorted` | whole state (44 stations) < 20 ms |
| Impact rebuild | ~13 min, fragile | STRtree already; add per-tile caching keyed by (station, replay) so only changed tiles recompute | < 2 min, resumable |

Measured, not claimed: `scripts/bench_latency.py` writes `results/latency/benchmarks.csv` (p50/p95 per path).

## Phase F — Frontend updates after accuracy + latency

| Page | Update |
|---|---|
| **New: Metrics** (or inside Data & Model) | precision / recall / F1 / MCC / PR-AUC per model at hour and event level, confusion matrix, threshold slider showing the precision-recall trade-off live, event table (detected? lead time) |
| Data & Model | coverage heatmap (source × month) with the chosen window highlighted; normalisation parameters table; model registry/version |
| Overview | KPI "floods detected / lead time" from event validation; data-freshness badge per source |
| Risk Map | buildings via tiles (fast); hybrid tier legend: *ML* vs *rainfall threshold* icon on each station; time scrubber over replay hours |
| Station drawer | which layer triggered the tier (ML probability vs IMD rainfall category), calibrated probability, confidence, SHAP drivers |
| Uncertainty | robustness + conformal from the new run; "sources online" from `/health/external` |
| System status (new, small) | API health + measured latencies (p50/p95) from the benchmark |
| Loader | only shown when a fetch actually exceeds 200 ms (already), now rarer because of tiling + caching |

## Phase V — Verify end to end
`python scripts/run_all.py` (data → notebooks → export → impact → audit) → `pytest` → `scripts/audit_pipeline.py` 0 FAIL → `npm run build` → screenshot check of every page.

---

## Order and checkpoints
1. **D1, D3, D4, D5** → checkpoint: coverage + tests green
2. **M1–M4, M6** (notebooks) → checkpoint: metrics table
3. **M5** hybrid tiers *(after your OK)*
4. **A1–A3** backend + API health → checkpoint: API tests green
5. **L** latency work + benchmark → checkpoint: budgets met
6. **F** frontend → **V** full verification
7. **D2** label curation (can run in parallel; when done, switch to Window C and rerun 2 → 6)

## Decisions needed from you
1. **Training window**: start with **A (2022-02 → 2023-08)** now? *(recommended)*
2. **Curate 2023-09 → 2025-12 labels** from public disaster reports (D2), so all sensors overlap? *(recommended, slower)*
3. **Hybrid warning tier** = max(ML, IMD rainfall threshold) (M5)? *(recommended: this is what makes real cloudbursts go red)*
