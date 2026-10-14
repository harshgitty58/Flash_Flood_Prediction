# PRAHAR — Industry-Standard Upgrade Plan
Goal: move from "well-engineered course project" to a system evaluated and trained the way operational
flood-warning services (IMD / CWC / WMO-style verification) would accept.
Principle: **fix evaluation first, then data, then training**. Better metrics on the current model tell us what to improve.

---

## Phase 1 — Industry-standard evaluation (≈ 1-2 days) · *do first*
**Why:** today's hour-level ML metrics are harsher than how warnings are judged, and miss the standard verification scores.

| Add | Definition / method | Where |
|---|---|---|
| **POD, FAR, CSI, ETS, HSS** | contingency-table scores (WMO verification standard) at ≥ ALERT and ≥ SEVERE | Metrics page + report |
| **District-day evaluation** | one warning per district per day (max tier of its gauges) vs flood recorded that day; also keep station-hour | `src/verification.py` |
| **Brier Skill Score** | BSS = 1 − Brier / Brier(climatology); climatology = base rate per district × season | replaces raw Brier as headline |
| **Reliability diagram + ECE** | 10-bin calibration curve, expected calibration error | Metrics page |
| **Bootstrap 95 % CIs** | block bootstrap by event (1,000 resamples) for every score | all tables |
| **Baselines** | climatology, persistence (yesterday's flood), rainfall-threshold-only, district-prior-only | every table shows *skill over baseline* |
| **Honest lead time** | from the first *transition* NORMAL/WATCH → ALERT that persists ≥ 3 h, ignoring alarms already on 24 h earlier | replaces the window-saturated metric |
| **Cost-loss / economic value** | relative value curve over cost/loss ratios | shows when warnings are worth acting on |
| **Breakdowns** | per district, month, gauge density, trigger (ML vs rainfall) | Metrics page |

**Acceptance:** every headline number has a baseline, a skill score and a 95 % CI; FAR / CSI reported at district-day level.

## Phase 2 — Data and labels (≈ 1-2 weeks) · *biggest lever on accuracy*
| Item | Source (open) | Purpose |
|---|---|---|
| **Complete flood labels 2023-09 → 2025-12** | Uttarakhand SDMA / NDMA daily situation reports, IMD event logs, CWC bulletins; every event with date, district, block, source | 2-3× more events; unlocks training window C (all sensors overlap) |
| **Label quality** | tag each event: type (cloudburst / flash flood / landslide), location precision (village / block / district), confidence | weight or filter noisy labels |
| **Gridded rainfall** | IMD 0.25° daily gridded, **GPM IMERG** 0.1° half-hourly | fills gauge gaps; independent second rain source (enables source-agreement) |
| **Soil moisture** | ERA5-Land / SMAP | antecedent wetness (strong flash-flood driver) |
| **Terrain** | Copernicus GLO-30 DEM | slope, flow accumulation, HAND, **upstream catchment per gauge** |
| **Rainfall forecasts** | NCMRWF / GFS 0.25° (24-72 h) | turns nowcasting into forecasting with real lead time |
| **Discharge** | match each gauge to its upstream/downstream CWC station via the river network | discharge currently contributes nothing |

**Acceptance:** ≥ 60 labelled district-events in the training window; every gauge has a catchment polygon and a satellite-rain twin.

## Phase 3 — Normalisation and features (≈ 3-5 days)
- **Station-relative normalisation:** convert rainfall to each gauge's own climatological percentile / return period (fitted on train years only). 100 mm means different things in Dehradun and Pithoragarh.
- **Seasonal standardisation:** z-scores within month-of-year to remove the monsoon cycle, so the model learns *anomalous* rain.
- **Catchment aggregation:** area-weighted rain over each gauge's upstream catchment (gauge + IMERG), not only the point gauge.
- **Missingness as signal:** explicit mask features plus sensor-age instead of silent median imputation; robust to outages.
- **Physically motivated indices:** rain intensity-duration exceedance (vs regional I-D thresholds), antecedent soil moisture × rain, slope × flow accumulation.
- **Versioned transforms:** one `FeatureNormalizer` artefact per data version, saved with the model (already in place; extend to the new methods).
- **Drop pure location priors** (district constants) from the *timing* model; keep them only in a separate susceptibility layer, so the model must learn *when*.

## Phase 4 — Full-scale training (≈ 1 week)
**Two-model design (industry pattern):**
1. **Susceptibility model** (static: terrain, landslides, flood history) → *where* floods tend to occur.
2. **Trigger model** (dynamic: normalised rain, soil moisture, forecasts, discharge) → *when*. Final risk = susceptibility × trigger, calibrated.

**Training protocol**
| Aspect | Plan |
|---|---|
| Unit | district-day (primary) + station-hour (nowcast) |
| Validation | **nested CV**: outer leave-one-year-out *and* leave-one-district-out; inner time-series CV for tuning; final hold-out = latest year, touched once |
| Imbalance | class weights + focal loss; event-level sample weighting (each flood event equal weight) |
| Models | climatology / threshold baselines → logistic (interpretable) → **LightGBM / XGBoost with monotonic constraints** (more rain never lowers risk) → temporal CNN / LSTM on 72 h sequences once labels ≥ 100 events → ensemble |
| Tuning | Optuna, 100-200 trials per model, objective = event-level CSI (or BSS) on inner folds |
| Uncertainty | deep ensembles / bootstrap ensembles + conformal calibration per season |
| Thresholds | chosen on validation to hit a **target FAR** (e.g. ≤ 0.5) at district-day level |
| Reproducibility | MLflow tracking (params, data hash, metrics, artefacts), fixed seeds, data versioning (DVC) |

## Phase 5 — Operational readiness (≈ 1 week)
- **Backtesting:** replay every monsoon 2022-2025 hour by hour exactly as live (no future data), with the published warning table.
- **Monitoring:** data-drift (PSI per feature), sensor freshness alarms, weekly skill tracking against new SDMA reports.
- **Model registry and release gates:** a new model ships only if district-day CSI and BSS beat the current model with non-overlapping CIs.
- **Model card + data sheet**, PDF situation reports, CI pipeline running tests + audit + verification on every change.

---

## Targets (to verify, not promises)
| Metric (district-day, ≥ ALERT) | Now (estimate) | Target after Phase 2-4 |
|---|---|---|
| POD | ≈ 0.47 (hour level) | ≥ 0.65 |
| FAR | ≈ 0.88 (hour level) | ≤ 0.50 |
| CSI | ≈ 0.11 (hour level) | ≥ 0.35 |
| Brier Skill Score vs climatology | ≈ 0 | ≥ 0.15 |
| Honest median lead time | not measurable | ≥ 3 h (nowcast), ≥ 12 h (with forecasts) |

## Order and effort
1. **Phase 1** (1-2 days): no new data needed; immediately makes results standard and comparable.
2. **Phase 2** (1-2 weeks): labels + IMERG + catchments are the biggest accuracy gain.
3. **Phase 3 + 4** together (≈ 2 weeks).
4. **Phase 5** when a deployable model exists.

## Decisions needed
1. Start Phase 1 now? *(recommended)*
2. For Phase 2, is pulling external datasets (IMERG, ERA5-Land, Copernicus DEM, SDMA reports) acceptable for the course scope?
3. Is a two-model design (susceptibility × trigger) acceptable, given it changes how the map's tiers are explained?
