# Remaining Tasks — Master Checklist

Compiled 2026-10-08, updated 2026-10-09 (model-truth pass), from: `Data Science Course Project (1).md` (objectives), `ANTIGRAVITY_OBJECTIVE_2_GUIDELINES.md`,
`ANTIGRAVITY_PHASE_3_OBJECTIVE_3_GUIDELINES.md`, `REMAINING_PHASES_PLAN.md` (Phase 4/5), `flood_intelligence_platform.md`
(product spec) and `PLATFORM_BUILD_PLAN.md` (web build), checked against what exists in the repo.

Legend: `[x]` done · `[~]` partial · `[ ]` not started · **P0** blocks the demo/report · **P1** strong differentiator · **P2** showcase

## Update: 2026-10-13 (labels, verification and model upgrades)
- **Done:**
  - District-name label-join fix (13 of 29 IMD flood days were dropped). Test ROC-AUC 0.53 → 0.71.
  - Multi-source 2022–25 label set (96 events) and the IMD vs SANDRP audit.
  - Label v2, rain-rule tuning, district-day model and E1–E3 experiments, all with pre-set adoption rules (see `LABELS_PLAN.md`, `MODEL_UPGRADE_PLAN.md`, `results/label_impact.md`, `results/model_upgrade.md`).
  - External validation on 29 events; Ground-truth panel on Metrics; "Districts to watch" ranking on Overview.
  - Impact layer covers every reporting gauge (5 km), with state-wide OSM place names.
- **Open (data, not models):**
  - Complete 2024–25 event list: USDMA SEOC daily reports via RTI.
  - Radar or satellite rain (IMD Doppler / GPM IMERG) to see cloudbursts between gauges.
  - Sections G–K below (DB, reports, auth, Docker) are unchanged.

## Update — 2026-10-11 (see `EXECUTION_PLAN.md` status for numbers)

**Done this block:** A1 · A2 · A3 · A8 (drifting counters removed from the final model) · A9-partial (12 curated 2024-25 events, used as external validation) ·
B1 · B2 · B3 · B4 (hybrid ML + IMD rainfall) · B5 · B6 (notebooks 09-14 executed + `phase4_report.md` + inference artefacts) ·
C3 · C8 (lazy routes + building tiles; MapLibre chunk still 1.3 MB) · D3b · F1 · F2 · F3 · F4 (`/predict/scenario`) · F7 (typed models, timing header) ·
J1 (layout, `requirements.txt`) · J3 (29 tests) · J5-partial (tier lifts / thresholds in JSON) · J6-partial (System page lists every external service) · K1 (README) · K2-partial (FastAPI `/docs`).
New: data-coverage analysis + Window A, parameterised normalisation, offline-gauge handling, label-day fix, O(1) online features, lookup-table calibration,
vectorised impact build (~1 min), `run_all.py` + `audit_pipeline.py` (0 fail), Metrics + System pages.

**Still open (priority order):**
1. **A9** — curate *all* (not only major) 2023-09 → 2025-12 flood days, or adopt an official SDMA daily log, so Window C (2023-06 → 2025-12, all sensors) can be used for training.
2. Rainfall layer calibration — per-district / per-season IMD thresholds (July 2023 validation precision 0.01 → too many rainfall alerts).
3. **G1-G4** PostgreSQL + PostGIS (backend currently serves files from memory).
4. **H1-H6** PDF situation report + exports.
5. **I1-I3** auth, alert subscriptions, audit log.
6. **J2** docker-compose · **J4** CI · **J7-J8** monitoring + deploy.
7. **A5 / A6** DEM features, soil moisture, satellite rainfall · **D4** HAND inundation extent.
8. **C4** time scrubber · **C5** event replay animation · **C7** /field mobile view.

---

## Status at a glance

| Track | State |
|---|---|
| Obj 1 — Curation | `[~]` rainfall, discharge, flood, landslide, district done; **soil moisture & terrain/DEM missing** (both listed in the objective) |
| Obj 2 — Cleaning & features | `[x]` duplicate bug fixed; labels limited to inventory coverage |
| Obj 3 — Training & evaluation | `[x]` re-done honestly: leave-one-event-out CV, location-free final model (Exp D, ROC-AUC 0.86 pooled) |
| Obj 4 — Uncertainty & robustness | `[~]` conformal + Venn-Abers, SHAP, warning tiers, lead time done; robustness (B3) + notebooks + report left |
| Web platform (`web/`) | `[~]` PRAHAR branding, landing + 7 console pages, building-level impact map; **static JSON only — no backend, no database** |
| Backend / DB / documents | `[ ]` nothing yet (sections F–K) |

---

## A. Data & model fixes (do first — they change every number downstream)

- [x] **A1 — Duplicate station-hours.** Root cause: Almora_1 reports two coordinate pairs → `compute_station_landslide_features` emitted 2 rows → merge fanned out. Fixed in `src/spatial.py` (modal coordinate per station); dataset now 21,464 rows, 0 dups. Original note: Final dataset has 21,982 rows but only 21,464 unique `(station, datetime)`; prediction CSVs carry the same duplicates. Find the join that fans out (likely landslide/spatial join in `src/spatial.py` / `station_landslide_features`), dedupe, re-run notebooks 04→08.
- [x] **A2 — Location leakage.** Added Exp F (no lat/lon); final model = Exp D (rain + discharge + flood history + landslide, no coordinates/calendar), chosen by event CV. Original note: `latitude`/`longitude` = 38% of XGBoost gain → model memorises flood locations. Retrain a variant without raw lat/lon (keep landslide/terrain proxies) and compare on test.
- [x] **A3 — Val→test collapse. Root cause: flood labels end 2023-08-26** (IMD inventory), so 2024–26 rows were all labelled 0. Now: rows past coverage are `NaN` (unlabelled, replay only); 7,830 labelled rows / 44 positives; `src/event_cv.py` leave-one-event-out CV (6 episodes) gives the trustworthy metrics. Original note: Investigate: tiny positive count (44 positives total, 17 in test), threshold tuned on 19 val positives, distribution shift 2023→2026. Options: rolling-origin CV, event-level (not hour-level) evaluation, class-weight / focal tuning, calibrate (isotonic) before thresholding. Report honestly either way.
- [ ] **A4 P1 — `model_registry.csv`** has two runs per model with empty metrics on the first; keep only the final run.
- [ ] **A5 P1 — Missing modalities from Objective 1:** add **DEM/terrain** (SRTM/Copernicus 30 m: slope, elevation, HAND/flow-accumulation at station) and **soil moisture** (SMAP L3 / ERA5-Land). Without these the "multimodal" claim rests on 4 sources. Re-run fusion ablation with them (Exp F/G).
- [ ] **A6 P2 — Satellite precipitation** (GPM IMERG half-hourly) as an independent rainfall modality → enables real "source agreement".
- [ ] **A8 P0 — Stale history features in the replay period.** `days_since_last_flood_prior_t` / `historical_flood_count_prior_t` keep drifting after 2023-08 because no newer events are in the inventory (e.g. 1,107 days at Yamuna Colony) → model extrapolates. Fix together with A9.
- [ ] **A9 P0 — Extend flood labels 2023-09 → 2026** (curate documented Uttarakhand flood/cloudburst events from NDMA/SDMA/IMD reports, with sources). Unlocks a real 2024–26 test set and fixes A8.
- [ ] **A7 P1 — River discharge ends 2025**; 2026 replays show it as MISSING. Either extend the CWC pull or pick a replay moment where discharge is present.

## B. Objective 4 — Uncertainty-aware & robust prediction (from REMAINING_PHASES_PLAN)

- [x] **B1 — 4A Conformal prediction** (`src/conformal.py`): Venn-Abers calibration + Mondrian conformal sets. 90 % coverage on test: 98.2 % overall, 17/17 floods; 75 % of sets are UNCERTAIN; Brier 0.076 → 0.027. Original plan: — `src/conformal.py`, `notebooks/09_conformal_prediction.ipynb`; calibrate on val, coverage at 80/90/95 % on test → `results/conformal/*`.
- [x] **B2 — 4B SHAP** (`src/explain.py`): global importance, per-district means, top-3 drivers per prediction, bar chart. Original plan: — `src/explain.py`; global summary + per-prediction top drivers → `results/shap/*` (`shap` is installed).
- [ ] **B3 P0 — 4C Robustness** — `src/robustness.py`, `notebooks/10_robustness.ipynb`; R1 noise, R2 station outage, R3 discharge failure, R4 feature dropout, R5 combined → `results/robustness/*`. This is the real "missing-data impact" table the UI needs (inference-time masking, unlike the retrain ablation shown now).
- [x] **B4 — 4D Warning levels** (`src/warning_levels.py`): 5 tiers on calibrated probability (1 / 5 / 15 / 35 %), conformal FLOOD set ⇒ ≥ ALERT; rationale + confusion in `results/warning_levels/`. SEVERE hit-rate 15 % on val (27× base); ≥ALERT recall on test 2/17. Original plan: — `src/warning_levels.py`. **Reconcile tiers:** the Phase 4 plan uses 4 tiers (CLEAR/WATCH/WARNING/ALERT, cut-offs .15/.40/.70 + uncertainty bump); the product spec and current UI use 5 (NORMAL→EXTREME, cut-offs .15/.30/.50/.75 set in `scripts/export_frontend_data.py`). Pick one, justify in `warning_design_rationale.md`, use it everywhere.
- [x] **B5 — Lead time** (`src.event_cv.lead_times`): 4/10 held-out district floods detected at 5 % hourly false-alarm rate, median lead 20.5 h (3–38 h). Original plan: — event-level evaluation: hours between first ≥ALERT prediction and recorded event, on held-out events only. Until then UI shows "pending".
- [~] **B6 P1 — 4E Inference artifacts**: model + predictions + conformal/warning outputs exist; still need `inference_artifacts/` bundle, notebooks 09/10 and `phase4_report.md`. Original plan: — `results/inference_artifacts/` (model, q̂, feature list, thresholds, explainer) + `results/phase4_report.md`.

## C. Web platform (`web/`)

Done: export script, PRAHAR branding (logo, forest theme), landing, app shell, Overview, Risk Map, Impact (building outlines + landmarks), Uncertainty (fusion ablation), Data & Model, basic Forecast/Events, river loading overlay (>200 ms), hover location/coordinates.

- [x] **C1 P0 — Basemap switcher: Dark / Satellite / Terrain + 3D toggle** (this session).
- [x] **C2 P0 — Impact v1: building exposure from ML-derived footprints** (this session) — see section D.
- [x] **C3 — Phase 4 outputs wired**: calibrated probability, tier, confidence, 90 % set, SHAP drivers (drawer), conformal coverage (Uncertainty), event-CV table (Model), lead time (Forecast). Robustness table still pending B3. Original plan: into export: CP interval + confidence (drawer, KPI, Forecast band replaces station-spread band), SHAP drivers (drawer "why"), robustness table (Uncertainty page), tiers from B4.
- [ ] **C4 P1 — Time scrubber on Risk Map** (step through replay hours; export per-hour snapshots).
- [ ] **C5 P1 — Event replay** (Events page): pick held-out events, T−6h→T animation, predicted vs observed, hit/miss/false-alarm.
- [ ] **C6 P1 — Source agreement** score per station (needs ≥2 independent rainfall sources → A6).
- [ ] **C7 P2 — Zone comparison**, auto report (PDF), `/field` mobile card + PWA manifest.
- [~] **C8 P2 — Code-split**: routes are lazy-loaded; MapLibre core chunk is still 1.3 MB → split it into its own vendor chunk.
- [ ] **C9 P2 — Deploy** static build (GitHub Pages / Netlify) for judges.

## D. Impact / exposure module (product spec §4–7)

- [x] **D1 — Building footprints from a pretrained model**: Microsoft Global ML Building Footprints (polygons extracted from satellite imagery by Microsoft's pretrained deep segmentation network) for the high-risk replay cluster.
- [x] **D2 — OSM infrastructure**: rivers/streams, roads, bridges, schools, hospitals for the same areas.
- [x] **D3 — Exposure proxy**: buildings within the risk radius of a ≥SEVERE station *and* close to a mapped waterway; prototype impact score. **Labelled as proxy, not inundation.**
  - Result (replay 05 Sep 2026, `scripts/build_impact_layer.py`): 36,552 ML-detected buildings within 6 km of 6 SEVERE stations; 5,166 scored MODERATE+ (99 critical, 2,169 high); 73 bridges, 108 road segments; OSM has 0 schools/hospitals mapped there (OSM gap, not absence).
- [x] **D3b — Building outlines (coloured by impact class) + OSM landmarks + open-source place labels** on Risk Map and Impact. All 36,552 buildings scored with DEM height-above-river (HAND-like) + distance to river; 565 named landmarks from OSM.
- [ ] **D3c P2 — Roads coloured by exposure** (lines, same scoring).
- [ ] **D4 P1 — Replace proxy with real extent**: HAND (height above nearest drainage) from DEM (A5) → depth-threshold inundation; then building impact = f(P, depth, footprint % inundated).
- [ ] **D5 P2 — Run our own pretrained detector** on Esri/Sentinel tiles (TorchGeo or SAM-based building segmentation; `torch` is installed) for a "fresh imagery vs MS footprints" comparison on one village. Demo-only, after D1–D4.
- [ ] **D6 P1 — Risk priority** = hazard × exposure × uncertainty, documented formula, shown per zone.

## F. Backend API (FastAPI) — bare minimum

Today the web app reads static files from `web/public/data/`. A real deployment needs a service between the UI, the model and the data.

- [ ] **F1 P0 — Service skeleton** `backend/`: FastAPI + Uvicorn, `pydantic-settings` config from `.env`, CORS for the web app, `/health` and `/version` (model version, data freshness).
- [ ] **F2 P0 — Read endpoints replacing the JSON files** (same shapes, so the frontend swap is one `fetch` base URL):

  | Endpoint | Replaces |
  |---|---|
  | `GET /stations` | `stations.json` |
  | `GET /risk/snapshot?at=` | `snapshot.json` |
  | `GET /risk/timeline?from=&to=&station=` | `timeline.json` |
  | `GET /model/summary` | `model.json` |
  | `GET /events` , `GET /events/{id}` | `events.json` |
  | `GET /impact/summary?run=` | `impact.json` |
  | `GET /impact/buildings?bbox=&zoom=` (or vector tiles `/tiles/{z}/{x}/{y}.pbf`) | 8.7 MB `buildings.geojson` (load by viewport) |
  | `GET /landmarks?bbox=` | `landmarks.geojson` |

- [ ] **F3 P0 — Inference endpoint** `POST /predict` → loads `models/xgboost/model.joblib` (+ conformal q̂, SHAP explainer from B6) once at startup; input = station + timestamp (features built server-side) or a raw feature row; output = the ML contract in spec §23 (probability, interval, confidence, tier, drivers, data-quality flags).
- [ ] **F4 P1 — What-if simulator** `POST /predict/scenario` (override rain_24h / discharge / drop a source) → powers a "what if 120 mm falls in 6 h?" panel and live sensor-dropout demo (ties to B3).
- [ ] **F5 P1 — Impact run endpoint** `POST /impact/run` → runs `build_impact_layer` logic for a given snapshot as a background job; `GET /jobs/{id}` for status.
- [ ] **F6 P1 — Ingestion jobs** (APScheduler or a cron container): pull new CWC rainfall/discharge, recompute features (`src/` pipeline), score, write predictions to DB. Even if only run manually for the demo, it must exist as code.
- [ ] **F7 P1 — Errors & validation**: typed request/response models, consistent error JSON, request logging, timeouts on external calls (Overpass, tile servers).

## G. Database (PostgreSQL + PostGIS) — bare minimum

- [ ] **G1 P0 — Schema + migrations** (SQLAlchemy 2 + Alembic), `docker-compose` service `db` with PostGIS image.

  | Table | Key columns |
  |---|---|
  | `stations` | id, name, district, kind (rain/river), geom (Point 4326), active |
  | `observations` | station_id, ts, rainfall_mm, discharge, quality_flag — index (station_id, ts) |
  | `features` | station_id, ts, feature JSONB, pipeline_version |
  | `model_versions` | id, name, path, metrics JSONB, thresholds JSONB, trained_at, is_active |
  | `predictions` | station_id, ts, model_version_id, p, lower, upper, tier, drivers JSONB |
  | `flood_events` / `landslides` | inventory rows + geom |
  | `buildings` | id, source (MS footprints), geom (Polygon) — GIST index |
  | `impact_runs` / `building_impact` | run_id, snapshot ts, method; building_id, score, h_above_river, dist_river |
  | `landmarks` | osm_id, name, kind, geom |
  | `reports` | id, type, params JSONB, file_path, created_by, created_at |
  | `users`, `alert_subscriptions`, `audit_log` | see I |

- [ ] **G2 P0 — Seed/load scripts**: CSV/parquet → tables (stations, observations, predictions from `results/predictions`, inventories, buildings, landmarks). One command: `python -m backend.seed`.
- [ ] **G3 P1 — Spatial queries in SQL** (`ST_DWithin`, `ST_Intersects`) instead of Python loops for impact; buildings served per bbox.
- [ ] **G4 P2 — Time-series scale**: TimescaleDB hypertable on `observations`/`predictions` if data grows; backups (`pg_dump` nightly).

## H. Document generation — bare minimum

- [ ] **H1 P0 — Situation report PDF** `GET /reports/situation?at=` : Jinja2 HTML template → PDF (WeasyPrint or Playwright `page.pdf()`). Contents: header with logo/time, risk summary, top-N stations table with tier + interval, static map snapshot, exposure counts by class, top exposed landmarks, data-source health, model version, disclaimer ("estimates, not damage/evacuation decisions").
- [ ] **H2 P1 — Zone / station brief** (1 page): station card + drivers + nearby exposed buildings/landmarks.
- [ ] **H3 P1 — Exports**: CSV of exposed buildings/landmarks, GeoJSON of current risk + impact layer (for QGIS / district GIS teams).
- [ ] **H4 P1 — Model card PDF/Markdown** auto-generated from `model_versions` (data, metrics val vs test, limitations, leakage note).
- [ ] **H5 P2 — Event post-mortem report** (predicted vs observed timeline for a historical event, from C5).
- [ ] **H6 — UI hooks**: "Download report" button on Overview/Impact, report history list (from `reports` table).

## I. Users, alerts & audit — bare minimum

- [ ] **I1 P1 — Auth**: login (JWT, hashed passwords) with 2 roles — `analyst` (full console, run impact/reports) and `viewer` (read-only). Public landing stays open.
- [ ] **I2 P1 — Alert rules**: subscribe to a district/station + tier threshold; when a new prediction crosses it, send email (SMTP) and store in `alerts` table; in-app notification bell. SMS/WhatsApp only as a stub.
- [ ] **I3 P1 — Audit log**: who generated which report / ran which impact job / changed thresholds.
- [ ] **I4 P2 — Field view** `/field` (spec §16) reading the same API, PWA installable.

## J. Engineering basics — bare minimum

- [ ] **J1 P0 — Repo layout & env**: `backend/`, `web/`, `src/` (ML), `scripts/`; `requirements.txt`/`pyproject.toml` pinned (pandas, xgboost, shapely, fastapi…); `.env.example`; no secrets in git.
- [ ] **J2 P0 — docker-compose**: `db` (PostGIS) + `api` (FastAPI) + `web` (nginx serving `web/dist`, proxy `/api`). One command `docker compose up`.
- [ ] **J3 P0 — Tests**: pytest for feature builders, scoring function, warning tiers, API endpoints (TestClient), seed script; frontend `tsc` + build in CI.
- [ ] **J4 P1 — CI** (GitHub Actions): lint (ruff, oxlint), tests, frontend build on every push.
- [ ] **J5 P1 — Config not code**: tier cut-offs, impact weights (0.7/0.3, 25 m, 500 m, 6 km), replay time → settings/DB, not constants in scripts.
- [ ] **J6 P1 — Data licences & attribution page**: Microsoft footprints (ODbL), OSM (ODbL), Esri imagery/labels, CARTO, AWS Terrarium, CWC/IMD/GSI sources.
- [ ] **J7 P2 — Logging/monitoring**: structured logs, `/metrics`, ingestion freshness alarm ("rain data > 3 h old").
- [ ] **J8 P2 — Deploy**: one VM / Render / Railway for api+db, static web on Netlify/Vercel; HTTPS.

## K. Documentation — bare minimum

- [ ] **K1 P0 — README** (replaces E4): what PRAHAR is, architecture diagram, setup (docker or local), how to re-run pipeline → seed → serve.
- [ ] **K2 P1 — API docs**: FastAPI `/docs` (OpenAPI) + short `docs/api.md` with example calls.
- [ ] **K3 P1 — Methodology doc**: features, model, uncertainty, warning tiers, impact score — with the "what not to claim" list (spec §25).
- [ ] **K4 P2 — User guide**: 1-page demo walkthrough with screenshots (also feeds E3).

## E. Report & submission

- [ ] **E1 P0** — Update `results/model_evaluation/phase3_model_report.md` after A1–A3.
- [ ] **E2 P0** — Phase 4 report (B6) + final course report covering Objectives 1–4, citing the 12 papers in the course doc.
- [ ] **E3 P1** — Demo script rehearsal (spec §29) on the final replay moment; screenshots for the report.
- [ ] **E4** — merged into K1.

---

## Suggested order
1. **Model truth first:** ~~A1 → A2/A3 → B1 → B2 → B4~~ done → **A9 + A8 (labels 2023-09→2026)** → B3 → B6.
2. **Minimum platform:** J1 → G1 → G2 → F1 → F2 → F3 → switch frontend to API → H1 → J2 → J3.
3. **Then:** C3 → B3/F4 → B5/C5 → I1/I2 → H2–H4 → A5 → D4 → K1–K3 → E1/E2 → the rest.

Bare-minimum "real project" cut = A1–A3, B1, B2, B4, F1–F3, G1–G2, H1, I1, J1–J3, K1.
