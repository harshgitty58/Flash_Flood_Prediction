# PRAHAR: Uttarakhand Flash-Flood Intelligence
*Predict · Prepare · Protect*

Multimodal, uncertainty-aware flash-flood warning for Uttarakhand.
- **Inputs:** CWC rain and discharge gauges, USDMA state weather stations, ERA5 reanalysis, IMD flood records, a multi-source 2022–25 event list, GSI landslides and district indices.
- **Models:** calibrated XGBoost plus IMD rainfall thresholds, combined into hybrid warning tiers, with a daily district ranking.
- **Map:** building-level exposure around every rain gauge, on a satellite/terrain map with state-wide place names.

## Quick start
```bash
pip install -r requirements.txt          # pandas, xgboost, scikit-learn, shap, shapely, fastapi, nbclient, pytest, pypdf, openpyxl …
python scripts/run_all.py                 # whole chain: data → labels → train → event CV → calibration → tiers → label audit
                                          # → experiments → external validation → verification → reports → export → impact → tests → audit
python scripts/run_all.py --from export   # only re-export JSON, impact layer, tiles, tests, latency, API check, audit

cd web && npm install && npm run dev      # static mode (reads web/public/data)
```
With the live API:
```bash
python -m uvicorn backend.app:app --port 8000
cd web && npm run dev:api                  # Vite proxies /api → :8000 (mode file web/.env.api)
```
API security: CORS is an allow-list (`params.yaml` → `api`, or `PRAHAR_CORS_ORIGINS=https://a.example,https://b.example`). `POST /admin/reload` is disabled unless `PRAHAR_ADMIN_TOKEN` is set on the server, and then needs the header `X-Admin-Token`.
`python scripts/run_notebooks.py` re-executes notebooks 09–14, the step-by-step record of the run.

## Layout
| Path | What |
|---|---|
| `curated_dataset/` | raw curated sources, read directly by the pipeline; `MANIFEST.sha256` pins every file (checked by tests and the audit) |
| `data/external/` | downloaded sources (not in git): ERA5, USDMA hydromet, DEM tiles, building footprints, OSM; only the derived label set in `labels/*.csv` is versioned |
| `params.yaml` | every quality-control, feature, tier, rain-rule, impact and API constant in one place (read through `src/params.py`) |
| `src/` | pipeline, features, target, training, event CV, calibration, warning tiers, verification, label audit and experiments, district-day model; `terrain.py` (Priority-Flood D8, flow accumulation, slope, aspect, TRI, TWI, SPI, HAND) |
| `backend/` | FastAPI service: data endpoints, `/predict`, `/predict/scenario`, `/health/external` |
| `web/` | React + MapLibre frontend |
| `scripts/` | label building, export, impact layer, tiling, reports, latency benchmark, API checks, end-to-end audit |
| `tests/` | data contracts, raw-file hashes, label set, online-vs-batch features, terrain algorithms, API contract and security (47 tests) |
| `results/` | every metric and report: `label_impact.md`, `model_upgrade.md`, `verification/`, `metrics/`, `labels/` … |

## Data window and labels
- Rainfall runs 2022-02 → 2026-09, discharge 2023-06 → 2025-12, and IMD flood labels end on 2023-08-26.
- Models train on **Window A (2022-02 → 2023-08-25)**. Later hours are replay.
- `scripts/build_labels.py` merges IMD, SANDRP, Sphere India situation reports, EM-DAT and a curated news list into **96 documented events (2022–25)**, each with a source and a date confidence.
  - Events after 2023-08 are an **external validation set**, never training labels, because "no report" doesn't mean "no flood".
  - Plans and decisions are in `LABELS_PLAN.md` and `MODEL_UPGRADE_PLAN.md`.

## Headline results (test month Aug 2023, after the label-join fix)
- **XGBoost:** ROC-AUC 0.71, PR-AUC 0.15 (base rate 5.8 %), F1 0.32. Before the district-name fix these were 0.53 / 0.04 / 0.08.
- **Hybrid tiers at ≥ ALERT:** station-hour precision 0.23, recall 0.65.
- **District-day CSI at ≥ ALERT** (hybrid, Aug 2023 test), by definition of a "flood day":
  - **0.095** (POD 0.70, FAR 0.90, 95 % CI 0.03–0.17): strict WMO-style, flood starting on day D and warnings counted D−1..D (`results/verification/verification.json`, shown on the Metrics page). Baselines: district prior 0.036, persistence 0.053.
  - 0.17 (POD 0.63, FAR 0.81): the training target's definition (flood on day D or D+1) (`results/warning_levels/rain_rule.json`).
  - XGBoost alone at its frozen threshold, same lenient definition: 0.15 against IMD labels and 0.20 against the fuller multi-source event list (`results/label_impact.md`).
- **External validation:** 7 of 21 documented post-2023 events were caught where a gauge was reporting.
- **Experiments tested and not adopted** (ensemble, event-fitted rain thresholds, district-day alerts, label v2): each was judged by a rule fixed before it ran.
  - The limit is the labels and the gauges' blindness to local cloudbursts, not the model class. See `results/model_upgrade.md`.

## Verifying a run
- `python scripts/audit_pipeline.py` checks that every stage exists, is newer than its inputs and agrees with the previous stage.
- `pytest -q -m "not network" tests` (47 tests) checks data contracts, raw-file hashes, the label set, feature equivalence, terrain algorithms and the API.
- GitHub Actions (`.github/workflows/ci.yml`) runs the tests and the web type-check/build on every push.

## What this is not
A decision-support prototype. It gives estimates of hazard and exposure with stated uncertainty, not damage, casualty or evacuation decisions.

## Plan and archive
- The full industry-grade roadmap is in `PRAHAR_MASTER_PLAN.md` (value audit, 24 workstreams, scoreboard, risks); `PRESENTATION_CHEATSHEET.md` lists every headline number with its definition.
- The hackathon Track B work ("Space mode": satellite flood-damage mapping) was moved out of this project to `../hackathon track-b/`; see the README there to restore it.

Attribution: Landing-page imagery contains modified Copernicus Sentinel data 2024–2025 (Sentinel-2 L2A via Earth Search, AWS Open Data) · terrain tiles: AWS Terrain Tiles (Terrarium) · buildings: Microsoft Global ML Building Footprints (ODbL) · © OpenStreetMap contributors (ODbL) · ERA5 / ERA5-Land via Open-Meteo (Copernicus Climate Change Service) · photographs: Wikimedia Commons (CC BY-SA, credited on the page).
