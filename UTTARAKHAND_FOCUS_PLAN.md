> **Superseded by `PRAHAR_MASTER_PLAN.md`** (kept for history). Its district-day CSI baseline of 0.169 uses the lenient "flood today or tomorrow" definition; the strict WMO figure is 0.095 (see V-37 in the master plan).

# PRAHAR: remove Track B, then a full-scale plan for the Uttarakhand project

Written 2026-10-20. Part A takes the hackathon Track B ("Space mode") out of the repo cleanly. Part B is the plan for the course project in `Data Science Course Project (1).md`: multi-source, uncertainty-aware flash-flood early warning for Uttarakhand.

Every "baseline" number below comes from a file in `results/` and is cited. Every "target" is a goal, judged by a rule fixed before the run, as `MODEL_UPGRADE_PLAN.md` already does.

---

# Part A: Remove Track B (Space mode)

## A0. What Track B is in this repo
Satellite damage mapping (Sentinel-1/2, Copernicus DEM, OSM, a U-Net trained on Kuro Siwo). It covers two case studies: Dharali 2025 and Trishuli (Nepal) GLOF 2026, checked against Copernicus EMSR927. It was added in commits `00e2813` → `f66c59d`.

The main project uses none of it. It doesn't feed the ML dataset, the models, the warning tiers or the verification. **One exception:** the Landing page shows Sentinel-2 landscape photos (`scripts/fetch_home_imagery.py`, `web/public/img/home/`). These belong to the main site and **stay**. Only a comment that mentions the "Track B rule" changes.

## A1. Safety first (5 min)
**Leave the existing git repo and its remotes untouched:** no commits, tags or pushes. The cleaned project goes to the **new repository** the owner will provide.
- The current repo (and its history up to `f66c59d`) is the Track B archive as it stands.
- Before deleting anything, copy the project folder (minus `.git`) to a working copy for the new repo, or `git init` fresh once the new remote URL is known.
- Move the untracked 174 MB `prahar_floodseg_v2.zip` out of the project folder, for example to `../_archive/`. Don't delete it yet.

## A2. Salvage before deleting (useful for Part B terrain features)
Two pieces of the Space-mode code are good, numpy-only algorithms the main project needs for the **Terrain / Hydrology** parameters (TWI, flow accumulation, SPI, HAND, catchment ID):

| Take from | Function | Becomes |
|---|---|---|
| `scripts/flowdir.py` | Priority-Flood D8 flow directions (Barnes et al. 2014) | `src/terrain.py::d8_flowdir()`, then flow accumulation, TWI and SPI at each gauge |
| `src/space/flood.py` | `hand()` height above nearest drainage | `src/terrain.py::hand()`, which replaces the HAND-like proxy in `scripts/build_impact_layer.py` (task D4 in `REMAINING_TASKS.md`) |
| `src/space/data.py` | `slope_percent()` | `src/terrain.py::slope()` |

Port the **algorithms only**. Their I/O uses `rasterio`, which is not in `requirements.txt`. Feed them the same AWS Terrarium tiles that `src/enrich_features.py` already reads with PIL, or Copernicus GLO-30 (see B2).

## A3. Delete (tracked in git)
| Path | What |
|---|---|
| `src/space/` (8 modules) | Space-mode pipeline |
| `scripts/export_space.py`, `check_emsr.py`, `capture_space.py`, `flowdir.py`, `s2_thumbs.py`, `make_trackb_notebook.py` | Space-only scripts (flowdir salvaged in A2) |
| `notebooks/trackB_train_floodseg_colab.ipynb` | U-Net training notebook |
| `models/space/` | `floodseg.onnx`, `floodseg_meta.json` |
| `results/space/` | Dharali and Trishuli outputs, `_cache/`, run logs |
| `web/src/pages/Space.tsx`, `web/src/components/TrackBCard.tsx` | UI |
| `web/public/data/space_index.json`, `space_dharali.json`, `space_trishuli.json` | exported data |
| `web/public/img/space/` | Sentinel-2 before/after + EMS images |
| `TRACKB_REPORT.md`, `TRACKB_WIN_PLAN.md`, `TRACK_B_PLAN.md`, `Track B (1).pdf` | hackathon docs |

Not tracked, delete or archive: `data/external/emsr927/` (12 MB), `prahar_floodseg_v2.zip`, and these files in `submission media/`: `14_…` to `27_…` (Space screenshots) and `16_dharali_flood_debris_cutoff_map.png`.
**Watch out:** `PRAHAR_demo_video*.mp4` and `PRAHAR_recording_script.pdf` probably show Space mode, so re-record them in Phase B5. Keep `01_…`–`13_…`.

**Keep:** `data/external/dem/` and `dem12/`, which the Impact layer and `src/enrich_features.py` use, and `web/src/components/PlaceSearch.tsx`, which Impact uses.

## A4. Edit (shared files)
| File | Change |
|---|---|
| `backend/app.py` | Delete lines 237–374: the whole Space block. Its imports (`re`, `subprocess`, `sys`, `threading`, `uuid`), `JOBS`, `STAGES`, `SpaceRun` and all `/space/*` routes are used nowhere else. `Response` and `Field` are still used above line 237, so keep them. |
| `web/src/main.tsx` | Remove the `Space` lazy import (l.17) and the `space` route (l.38). Add `<Route path="space" element={<Navigate to="/app" replace />} />` so old links still work. |
| `web/src/pages/AppShell.tsx` | Remove the `'Space · Track B'` nav group (l.11) and the `space` icon entry (l.15). |
| `web/src/pages/Overview.tsx` | Remove the `TrackBCard` import (l.6) and its full-width row (l.34). |
| `web/src/pages/Landing.tsx` | Remove the `TrackBCard` import (l.2) and the `#trackb` section (l.101–102). Put a **"Verified results"** card in its place, read from `metrics.json`: district-day CSI, external POD, lead time. Reword the comment on l.13 to "landscapes only, no people". |
| `web/src/lib/data.ts` | Drop `'space_index'` and `` `space_${string}` `` from the `useData` name union (l.78). |
| `scripts/capture_screens.py` | Remove the Space shots (l.51–56). |
| `scripts/fetch_home_imagery.py` | Comment only: drop "Track B rule". |
| `.gitignore` | Remove the `results/space/…` and `models/space/best.pt` lines (l.42, 43, 53, 54). |
| `README.md` | Delete the "Track B: Space mode" section and its attribution paragraph. Keep the Sentinel-2 credit for the Landing imagery. |

`requirements.txt`, `render.yaml`, `vercel.json` and `tests/` need **no change**. Track B's extra dependencies were never added to them, and no test covers `/space`.

## A5. Verify (definition of done)
```bash
git grep -n -i -E "space mode|track ?b|trackb|src\.space|emsr|floodseg|kuro|space_(index|dharali|trishuli)"   # → 0 hits (except this plan)
cd web && npm run build                      # tsc catches any dangling import
python -m pytest -q tests                    # API contract + data tests
python scripts/audit_pipeline.py             # 0 fail
python -m uvicorn backend.app:app --port 8000   # /docs lists no /space routes; /app/space redirects
```
Then make the first commit in the **new** repository (`PRAHAR: Uttarakhand flash-flood platform, main project only`) and push it to the new remote. Point Vercel and Render at the new repo, then re-capture the `01`–`13` screenshots. The old repo is never changed.

**Effort: about half a day.**

---

# Part B: Full-scale plan for the Uttarakhand project

## B0. Where we actually are (honest baseline)

| Metric (unit) | Value | Source |
|---|---|---|
| Station-hour test (Aug 2023), XGBoost | ROC-AUC **0.71** · PR-AUC **0.15** (base 5.8 %) · F1 0.32 | `results/metrics/metrics_summary.csv` |
| Event-CV pooled, deployed Exp G | ROC-AUC 0.70 · PR-AUC 0.19 | `results/event_cv/event_cv_summary.csv` |
| **Event-CV, rainfall-only (Exp A)** | ROC-AUC **0.50**: rain at the gauge is no better than chance | same |
| District-day, hybrid ≥ ALERT (test) | POD 0.63 · FAR 0.81 · **CSI 0.17** | `results/model_upgrade.md` |
| External validation, post-2023 events | **7/21 caught**, POD 0.33 [0.14–0.52] | `results/metrics/external_validation.json` |
| Brier Skill Score vs climatology | **0.07** · ECE 0.012 | `results/verification/verification.json` |
| Honest lead time (district-day) | 6/18 warned in advance, **median 3.5 h**; 7 already on, 5 missed | same |
| Conformal 90 % sets | coverage **0.884** (below nominal) · **85 % of sets UNCERTAIN** | `results/conformal/cp_summary.json` |
| Robustness, flood-history inputs removed | ROC-AUC 0.72 → **0.50** | `results/robustness/robustness_summary.csv` |
| Training data | 1.5 monsoons (2022-02 → 2023-08), ~50 IMD flood district-days, 37 gauges | `results/splits.json` |

**Diagnosis.** We changed the model class three times (E1–E3) without beating the deployed hybrid. Four facts in this table explain why:
1. **Too few labels.** There are about 50 training flood-days. Each district-day label is also copied to every gauge in the district, so the hourly positives are noisy.
2. **Too little history.** The models train on one and a half monsoons.
3. **The gauges miss cloudbursts.** Rainfall-only scores 0.50, and half of the documented floods had < 50 mm/24 h at the district's wettest gauge.
4. **The model mostly learned where floods happen, not when.** Removing the flood-history features drops it to chance.

**So the full-scale plan is mostly about data. Modelling comes second.**

## B1. Strategy: two complementary models, fed by complete data

| Layer | Unit | Years | Inputs | Why |
|---|---|---|---|---|
| **PREPARE**: district-day outlook (new core model) | district × day, 13 districts | **2001–2025** (~25 monsoons) | gridded rain (IMD 0.25°, GPM IMERG), ERA5/ERA5-Land, GloFAS discharge, static terrain/soil/land-cover, flood/landslide history | 10–20× more flood events; sees rain *between* gauges; gives real temporal and spatial generalisation tests |
| **NOWCAST**: station-hour (the current model, upgraded) | gauge × hour, ~44 gauges | 2022–2025 | CWC rain and discharge, CWC water level vs warning/danger levels, IMERG Early/Late, ERA5 CAPE/humidity, terrain at the gauge | hour-level timing and lead time in the monsoon |
| **Hybrid tiers** | district-day | — | PREPARE prior × NOWCAST trigger × IMD rain rule, with conformal uncertainty | one interpretable risk level (NORMAL → EXTREME) |

Both layers keep the spec's model ladder: **Logistic Regression → Random Forest → XGBoost → XGBoost + conformal → SHAP**.

## B2. Complete dataset plan: every parameter in the spec

Status: ✅ have · 🟡 partial · ❌ missing. "Acquire" names the source, with its access route in brackets.

| # | Spec group | Status now | Acquire / build | Feeds |
|---|---|---|---|---|
| 1 | **Precipitation** (1–72 h sums, max intensity, change, API, hours since onset) | ✅ CWC gauges 2022–26 · ✅ ERA5 · 🟡 USDMA hydromet | **GPM IMERG V07** half-hourly 0.1°, 2000→ (NASA GES DISC, Earthdata login; subset to 77.5–81.1 E, 28.7–31.5 N) · **IMD gridded 0.25° daily** 1901→ (`imdlib`) · add "hours since heavy rain started" | both |
| 2 | **Soil moisture** (surface, root zone, anomaly, percentile, Δ24 h, Δ72 h) | 🟡 ERA5-Land 0–7 and 7–28 cm, anomaly | ERA5-Land layers 3–4 (100–289 cm) for root zone (Copernicus CDS) · **SMAP L4 SPL4SMGP** 9 km 3-hourly 2015→ (NSIDC) · derive percentile, Δ24 h, Δ72 h | both |
| 3 | **Terrain** (elevation, slope, aspect, curvatures, TRI, TWI, flow accumulation, SPI, drainage density, distance to stream) | 🟡 elevation, slope, relief, TPI at the gauge (Terrarium z12) | **Copernicus GLO-30** (AWS open data) · `src/terrain.py` (salvaged D8 + HAND, A2) computes all 11 · per gauge **and** per catchment (area-weighted) | both |
| 4 | **Hydrology** (discharge and changes, rolling stats, anomaly, water level, level vs warning/danger) | 🟡 CWC discharge, 7 stations, 2023-06 → 2025-12 | **CWC flood-forecast stations** (ffs.india-water.gov.in / India-WRIS): water level plus official warning and danger levels · **GloFAS v4 reanalysis** daily 0.05°, 1979→ (CDS `cems-glofas-historical`) for every district outlet | both |
| 5 | **Flood history** (count, 5/10-yr frequency, days since last, severity, area, DFSI, hotspot) | ✅ IMD inventory, DFSI, area · ✅ 96 events 2022–25 (5 source families) | **Labels 2001–2021:** India Flood Inventory (IFI), IMD *Disastrous Weather Events* annual reports, EM-DAT, Dartmouth Flood Observatory, NDEM · **Labels 2024–25 completion:** USDMA SEOC daily reports (RTI), GDELT news mining. All features stay prior-only (no leakage). | both |
| 6 | **Landslide history** (count, density 5/10 km, distance, hotspot, prone zone) | ✅ GSI inventory, 5,443 points | **NASA Global Landslide Catalog** (dated, gives co-labels) · **ISRO Landslide Atlas of India 2023** (prone-zone indicator) | both |
| 7 | **Meteorology** (temperature, RH, wind, pressure) | 🟡 USDMA temperature only | ERA5 hourly: 2 m T, dewpoint→RH, 10 m wind, surface pressure, plus **CAPE and total-column water vapour**, the cloudburst precursors the gauges can't see | both |
| 8 | **Temporal** (hour, DOW, DOY, month, season, monsoon flag/phase) | 🟡 removed from the final model to avoid leakage | Keep only **monsoon phase** from IMD onset/withdrawal dates (`data/external/imd/monsoon_report`). Use it as a physical regime, not a calendar shortcut. | both |
| 9 | **Spatial** (lat/lon, station, district, catchment, elevation zone) | 🟡 district only (lat/lon dropped: leakage) | **HydroBASINS** level 7–8 catchment ID · elevation zone (< 1000 / 1000–2000 / > 2000 m) · Garhwal or Kumaon division | both |
| 10 | **Real-time IoT** | ❌ none exists | Document as out of scope. The robustness suite simulates sensor dropout and noise (R1–R5). Stretch goal: USDMA AWS feed. | — |
| 11 | **Optional RS** (runoff, SWE, land cover, land use, soil) | ❌ | ERA5-Land surface and sub-surface runoff and **snow water equivalent** · **ESA WorldCover 10 m** · **SoilGrids 250 m** (texture, bulk density) | PREPARE |
| 12 | **Targets** | 🟡 flood in next 24 h | Keep the 24 h primary target. Add **severity** (3 classes, from deaths and damage in the inventory), **event-level labels with confidence weights**, and a flag for non-rainfall events (GLOF, avalanche such as Chamoli Feb 2021) so they are **excluded**. | both |

**Accounts the team must create:** NASA Earthdata (IMERG, SMAP) and Copernicus CDS (ERA5-Land, GloFAS). **Paperwork:** file the USDMA RTI **this week**. It is the slowest item.

**Dataset deliverables**
- `data/processed/v3/district_day.parquet`: 13 districts × ~9,100 days.
- `data/processed/v3/station_hour.parquet`: 2022–2025.
- `results/data_dictionary.csv`: one row per spec parameter → column, source, unit, past-only window, or "N/A + reason".
- `tests/test_data_v3.py`: contracts for every new source (ranges, gaps, no future leakage).

## B3. Labels: the biggest lever
1. **Back-fill 2001–2021** from IFI, IMD DWE, EM-DAT and DFO, merged with the existing `scripts/build_labels.py` logic: source, date confidence, district. Expect **several hundred** district-days, against ~130 today.
2. **Complete 2024–25** with USDMA SEOC (RTI) and GDELT. With that, Window C (2023-06 → 2025-12, all sensors) becomes **trainable** and A8/A9 in `REMAINING_TASKS.md` close.
3. **Severity** label: 0 = none, 1 = flood without deaths, 2 = deaths or major damage.
4. **Label audit:** IMD vs SANDRP vs SEOC agreement, kept as `results/labels/label_audit_v3.json`.
5. **Rule kept:** "no report ≠ no flood". Days with no source coverage stay **unlabelled**, not 0.

## B4. Experiments: the 10 research questions in the spec

| Spec RQ | Experiment | Protocol |
|---|---|---|
| 1 Data fusion | Ablation over **11 source groups** (add one at a time, and leave one out) | event-grouped CV, both layers |
| 2 Model complexity | LR vs RF vs XGBoost on identical folds | same |
| 3 Degradation | R1–R5 at inference: noise, gauge outage, discharge failure, random dropout, combined | test years |
| 4 Uncertainty | XGBoost vs XGBoost + **Mondrian conformal by class and by division**, calibrated on **event-blocked** folds | coverage at 80/90/95 % |
| 5 Spatial generalisation | **Garhwal (7 districts) ↔ Kumaon (6)**, plus leave-one-district-out | PREPARE |
| 6 Temporal generalisation | **Rolling origin**: train ≤ Y−1, test Y, for Y = 2016…2025 · NOWCAST: train 2022–23, validate 2024, test 2025 | both |
| 7 Attribution | SHAP global, per season, per division · rank stability (Kendall τ) | both |
| 8 Threshold optimisation | cost-loss relative economic value, POD–FAR curves, tier cut-offs tuned on validation only | district-day |
| 9 Lead time | horizons 6 / 12 / 24 / 48 h · first sustained switch-on before the event | events |
| 10 Robustness × uncertainty | does conformal coverage hold under R1–R5? | test years |

Spatial generalisation stays inside Uttarakhand (Garhwal ↔ Kumaon). Himachal Pradesh and Sikkim are a **stretch phase** after the report is done. The same pipeline runs for them once their gridded data and labels are pulled.

## B5. Top metrics: the scoreboard
These five headline numbers go on the first slide and the Metrics page. The rest are supporting numbers. Every target is judged on held-out events or years, never on tuning data.

| # | Headline metric | Why it matters | Baseline | Target |
|---|---|---|---|---|
| 1 | **District-day CSI at ≥ ALERT** (with POD and FAR) | how warnings are issued and judged (WMO-style) | 0.17 (POD 0.63, FAR 0.81) | **≥ 0.25** with FAR ≤ 0.70 |
| 2 | **Event-CV PR-AUC** (pooled) | ranking quality under 5–8 % base rate; ROC-AUC alone hides this | 0.19 | **≥ 0.30** |
| 3 | **Brier Skill Score** vs climatology | are the probabilities actually useful? | 0.07 | **≥ 0.15** |
| 4 | **Conformal 90 % coverage gap** and **set efficiency** | the uncertainty component in the spec | 0.884 (−1.6 pts) · 85 % uncertain | **±2 pts of nominal for both classes** · uncertain **< 50 %** |
| 5 | **Useful lead time**: share of events warned ≥ 6 h ahead, and the median | the early-warning claim | 6/18 warned · median 3.5 h | **≥ 50 % of events** · median **≥ 12 h** |

**Supporting metrics**

| Metric | Baseline | Target |
|---|---|---|
| External POD, post-2023 events not used in training | 0.33 (7/21) | ≥ 0.50 |
| Rainfall-only ROC-AUC (shows the rain signal is real once gridded rain is added) | 0.50 | ≥ 0.65 |
| Robustness: ROC drop when flood history is removed | 0.22 | ≤ 0.10 |
| Robustness: ROC drop at 25 % input dropout | 0.07 | ≤ 0.05 |
| Spatial gap: Garhwal → Kumaon PR-AUC vs in-region PR-AUC | — | gap ≤ 30 % |
| Temporal gap: rolling-origin PR-AUC, worst year vs mean | — | reported with CI |
| ECE (reliability) | 0.012 | ≤ 0.02 kept |
| District ranking recall@3 | 0.34 (prior 0.21) | ≥ 0.45 |
| False alarms per district-month (monsoon) | from `verification.json` | report and cap by tier |
| `/predict` latency p95 | `results/latency/benchmarks.csv` | ≤ 200 ms |

**Reporting rules**
- Use 95 % block-bootstrap CIs over days. `src/verification.py` already does this.
- Always show the climatology, persistence, rain-rule and district-prior baselines next to the model.
- Write each adoption rule into the experiment's docstring before it runs.

## B6. Phased timeline (8 weeks; compress if the deadline is sooner)

| Week | Phase | Work | Done when |
|---|---|---|---|
| 0 (20–25 Oct) | **A: Track B removal** · accounts · RTI | Part A · Earthdata + CDS accounts · file the USDMA RTI | A5 checks pass |
| 1–2 | **B-data 1** | IMERG, IMD gridded, ERA5 atmospheric, ERA5-Land (soil moisture, runoff, SWE), GloFAS pulls (`scripts/fetch_*.py`) · `src/terrain.py` (GLO-30, 11 terrain features, HydroBASINS IDs) · WorldCover, SoilGrids | raw sources cached, contract tests green |
| 2–3 | **B-labels** | 2001–2021 back-fill · 2024–25 completion (GDELT now, SEOC when the RTI arrives) · severity · audit | `labels_2001_2025.csv` + audit report |
| 3–4 | **B-dataset v3** | build `district_day` and `station_hour` v3 · data dictionary covering all 12 spec groups · leakage audit · normalisation fitted on train only | `audit_pipeline.py` 0 fail, dictionary complete |
| 4–6 | **B-models** | LR/RF/XGB tuned with event-grouped CV on both layers · RQ 1, 2, 5, 6 · severity model · hybrid re-fit | experiment tables in `results/v3/` |
| 6–7 | **B-uncertainty & robustness** | Mondrian conformal, event-blocked · RQ 3, 4, 7, 8, 9, 10 · warning cut-offs re-tuned | scoreboard (B5) filled with CIs |
| 7–8 | **B-product & report** | export v3 to the web (Overview, Risk Map, Metrics, Uncertainty) · update the API · Phase 4 report, presentation, re-recorded demo · README and run-all reproducibility · CI (pytest + build on push) | `run_all.py` reproduces every number; deployed |
| stretch | HP + Sikkim | the PREPARE pipeline on two more states | cross-state transfer table |

## B7. Risks and fallbacks
| Risk | Fallback |
|---|---|
| RTI arrives late or never | GDELT and news mining for 2024–25. The rolling-origin test uses 2016–2023, which are labelled from IFI and IMD DWE. |
| IMERG is too coarse for cloudbursts (0.1°) | Still better than gauge-only between gauges. Report the limitation, and add IMERG max-in-catchment as a feature. |
| Back-filled labels are uneven (more reports in later years) | Add year as a covariate in the label audit only. Weight samples by label confidence. Report per-decade POD. |
| Render's 512 MB free tier | Keep the per-station cache pattern from `c185454`. The district-day model is small. |
| Targets not reached | Report honestly against the baselines. The B0 diagnosis is itself a result the report can stand on. |

## B8. Immediate next actions
1. Get the new repository URL, then run Part A (half a day) in a fresh working copy and push it there. The existing repo stays untouched.
2. Create the NASA Earthdata and Copernicus CDS accounts, and file the USDMA RTI.
3. Write `scripts/fetch_imerg.py`, `fetch_imd_grid.py`, `fetch_era5_atmos.py`, `fetch_glofas.py` and `src/terrain.py`.
4. Start the 2001–2021 label back-fill with `scripts/build_labels.py` as the base.
