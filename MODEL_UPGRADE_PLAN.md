# PRAHAR: Model Upgrade Plan

**Goal:** improve detection quality (PR-AUC, CSI, POD) and cut false alarms (FAR, alert burden) without fooling ourselves.

**Constraint:** there are only ~50 labelled flood district-days in 2022–23 (6 independent episodes). So the plan favours methods that work with few positives, or that can use the 2024–25 documented events. More complex models are not the answer here.


## Status (2026-10-13), full numbers in `results/model_upgrade.md`

| Exp | Result | Decision |
|---|---|---|
| E1 ensemble | Test ROC-AUC 0.708 → **0.784**, event-CV PR-AUC 0.188 → **0.205**; district-day CSI 0.150 → 0.145 (v1), 0.197 → 0.192 (v2) | **Not adopted** (CSI rule). Ranking gain reported. |
| E2 fitted thresholds | Event rainfall is low: hills ALERT/SEVERE/EXTREME = 12 / 42 / 108 mm/24 h. 2025 POD 2/10 → 5/10, but test CSI 0.169 → 0.088 and ALERT district-days roughly double | **Not adopted**. Key finding: half of documented floods had < 50 mm at the district's wettest gauge, so the gauges miss the cloudbursts. |
| E3 pooled district-day | Alert layer CSI 0.105 vs hybrid 0.169; ranking recall@3 **0.46** vs prior 0.41 (test), **0.34** vs 0.21 (external; chance 0.23) | Alert layer **not adopted**; **ranking view adopted** (Overview → "Districts to watch") |
| E4 / E5 | Not run: E1–E3 show the limit is labels and rain observation, not model class | Deferred |

Note on E2: the tier mapping in §2 was corrected before the run to ALERT = 20th, SEVERE = 50th, EXTREME = 80th percentile of event rainfall. The original text had the order inverted.

**Next (data, not models):** a complete 2024–25 event list (USDMA SEOC daily reports, RTI), and rain that can see cloudbursts between gauges (IMD Doppler radar mosaics or GPM IMERG half-hourly).

---

## 0. Current baseline (what every experiment must beat)

| Metric | Deployed (XGBoost + hybrid tiers) | Source |
|---|---|---|
| Test station-hour ROC-AUC / PR-AUC (base rate 5.8 %) | 0.708 / 0.150 | `results/model_evaluation/model_comparison.csv` |
| Event-CV pooled ROC-AUC / PR-AUC | 0.701 / 0.186 | `results/event_cv/event_cv_summary.csv` |
| Test district-day ≥ ALERT (hybrid): POD / FAR / CSI | 0.63 / 0.81 / 0.169 [0.09, 0.25] | `results/warning_levels/rain_rule.json` |
| External (29 events after Aug 2023): POD | 7/21 = 0.33 [0.14, 0.52] | `results/metrics/external_validation.json` |
| Alert burden, monsoon 2024 | 329 ALERT district-days, 4 % near a documented event | same |

## 1. Rules for every experiment

1. **Same data:** same splits (train < 2023-07-01, validation Jul 2023, test 1–25 Aug 2023), the same 23 features unless the experiment says otherwise, and the same verification code.
2. **Adoption rule written in the module docstring before the first run.** No re-running with a new rule after seeing the test results.
3. **Scored three ways:**
   - official IMD answer key (v1);
   - fuller answer key (v2, IMD + SANDRP + SitReps);
   - external events after Aug 2023 (POD + alert burden).
4. **Bootstrap CIs on every headline number.** A gain counts only when it holds on both answer keys and doesn't come with a higher alert burden.
5. **Time-honest data use.** Experiments that learn from 2024–25 events hold out **all 2025 events** and the **Aug 2023 test month**; those are used for scoring only.
6. **One output file per experiment** in `results/model_upgrade/`, plus a combined report `results/model_upgrade.md` with before → after tables.

---

## 2. Experiments (in order)

### E1. Equal-weight ensemble of the three models (hourly)
- **Idea:** Random Forest already beats XGBoost on test ROC-AUC (0.79 vs 0.71). Averaging three models with different error patterns usually helps when data is small.
- **Method:**
  - Average the LR, RF and XGBoost probabilities (equal weights, no tuning), then calibrate with Venn-Abers on validation.
  - Threshold and tiers use the same rules as now.
  - Event-CV is re-run for the ensemble.
- **Adopt if:** event-CV PR-AUC ≥ XGBoost's, **and** test PR-AUC and district-day CSI ≥ XGBoost's on both answer keys.
- **If adopted:** the backend loads three models. The latency budget (< 50 ms warm `/predict`) is re-checked by `tests/test_api.py`.
- **Output:** `src/ensemble.py` → `results/model_upgrade/e1_ensemble.json`. Effort: ~1 h.

### E2. Rainfall thresholds fitted on documented events (flash-flood-guidance style)
- **Idea:** the rainfall layer causes most false alarms. It uses one fixed IMD number (64.5 mm/24 h) for every district.
  - Operational flash-flood guidance, and the landslide-threshold literature (Caine 1980; Brunetti 2010; Peruccacci 2012), fit **rainfall-threshold curves from documented events** instead.
  - Fitting needs only the event rainfall plus normal rainfall climatology, not a complete no-flood list. So the **2024 events can be used legitimately**.
- **Method:**
  - For each documented event, take the triggering rainfall in its district from the best available source: the CWC gauge max, else USDMA hydromet, else ERA5. Measure 24 h, 72 h and peak 1 h.
  - Fit cumulated-rainfall-vs-duration curves `E = α·D^β` at the 5 % / 10 % / 20 % lower envelope of event points (frequentist method). Fit them separately for two susceptibility groups: hills (landslide hotspot or DFSI ≥ median) and plains.
  - Map the curves to tiers: 20 % curve → ALERT, 10 % → SEVERE, 5 % → EXTREME (only rain above these curves triggers). Cloudburst (≥ 100 mm/h) stays EXTREME.
  - **Fit on** events from 2022 – Jul 2023 and 2024 (any source, confidence ≥ medium). **Score on** the Aug 2023 test month and all 2025 events.
- **Adopt if:** on the test month, hybrid district-day CSI ≥ current, **and** on 2025 events, POD ≥ current, **and** monsoon-2024/2025 alert burden ≤ current. The curves are plain numbers, so the backend reads them from `warning_thresholds.json` (stays station-local).
- **Output:** `src/rain_thresholds.py` → `results/model_upgrade/e2_thresholds.json` + an E–D scatter plot with the fitted curves. Effort: ~half a day.

### E3. District-day model that shares strength across districts
- **Idea:** the district-day model ranks well (test ROC-AUC 0.78) but failed on its threshold, which was picked on 15 positives. Two fixes:
  - **partial pooling**: each district gets its own baseline risk, shrunk towards the overall mean (L2-penalised district intercepts, which is equivalent to random intercepts with a Gaussian prior);
  - **a stable threshold rule** that doesn't depend on 15 events.
- **Method:**
  - Same district-day dataset as `src/district_day.py` (CWC + hydromet + ERA5).
  - Add penalised district intercepts plus shared rain slopes.
  - Choose the threshold on training data so that the expected number of alert days = **2 × the observed flood-day rate** (frequency bias 2, an operational convention), instead of maximising CSI on validation.
  - Also report the **ranking use**: the top-k districts per day and the hit rate among them.
- **Adopt if:** the same three-part rule as in `src/district_day.py` (CSI vs hybrid, external POD, alert burden). Even if it isn't adopted, a "top-3 districts today" ranking view is offered if its top-3 hit rate beats the district-prior baseline.
- **Output:** extend `src/district_day.py` (variant `pooled`) → `results/model_upgrade/e3_district_pooled.json`. Effort: ~half a day.

### E4. Positive-unlabelled (PU) learning on 2023-06 → 2025-12 (optional, after E1–E3)
- **Idea:** the 2024–25 lists contain only reported floods, so a missing day means "unknown", not "no flood". PU learning (Elkan & Noto 2008) is built for exactly this, and it lets the district-day model train on ~3× more positives.
- **Method:**
  - District-day rows from Jun 2023 to Dec 2024. Positives = documented events (confidence ≥ medium); the rest is unlabelled.
  - Fit P(labelled | x), estimate c = P(labelled | flood) on held-out positives, then P(flood | x) = P(labelled | x) / c.
  - The test month and **all 2025 events are held out**.
- **Adopt if:** 2025 external POD ≥ current hybrid **and** test-month district-day CSI ≥ the E3 result **and** alert burden ≤ current.
- **Output:** `src/pu_district.py` → `results/model_upgrade/e4_pu.json`. Effort: ~1 day.

### E5. CatBoost in place of XGBoost (optional, quick)
- **Idea:** CatBoost's ordered boosting overfits less on small, noisy data.
- **Method:** same features, splits and threshold rule; a small fixed search space (depth 4–6, 300 iterations, early stopping on validation).
- **Adopt if:** the same rule as E1.
- **Output:** `results/model_upgrade/e5_catboost.json`. Effort: ~1 h (needs `pip install catboost`).

### Not doing (and why)
- **Deep learning** (LSTM, transformer, graph network over rivers): needs hundreds of events; with 6 episodes it would memorise them.
- **More features or more tuning:** adding ERA5, soil moisture and terrain already *lowered* event-CV (0.70 for H against 0.70 for G, with lower PR-AUC); bigger search spaces overfit 6 episodes.
- **Weather-forecast inputs:** they add lead time, not accuracy at the moment of the nowcast. That belongs to a later phase.

---

## 3. Order, effort and checkpoints

| Step | What | Effort | Checkpoint |
|---|---|---|---|
| 1 | E1 ensemble | ~1 h | decision recorded; backend latency test still passes |
| 2 | E2 fitted rainfall thresholds | ~½ day | curves plotted; tiers re-run; external + alert burden compared |
| 3 | E3 pooled district-day + ranking view | ~½ day | decision recorded; top-k hit rate vs district prior |
| 4 | Report + UI | ~2 h | `results/model_upgrade.md`; "Model upgrades" rows in the Metrics Ground-truth panel; PRESENTATION_CONTENT updated |
| 5 | E4 PU learning (if E1–E3 leave room) | ~1 day | decision recorded |
| 6 | E5 CatBoost (optional) | ~1 h | decision recorded |
| — | Full chain (`scripts/run_all.py`) green after each adopted change | — | tests + audit 0 fail |

Each experiment becomes a stage in `scripts/run_all.py`, so its numbers are always reproducible.

## 4. Realistic expectations
- **E1:** small, steady gain in ranking (+0.02–0.05 ROC-AUC). Little effect on false alarms.
- **E2:** the best chance of a real false-alarm cut, because it is the only experiment that learns from the 2024 events and it targets the layer that over-alerts.
- **E3:** unlikely to beat the hybrid as a yes/no alert, but likely useful as a **district ranking**.
- **E4:** highest ceiling, highest risk. The estimate of c rests on few positives, so its CI will be wide.
- If none is adopted, that is a valid result: it shows the limit is the labels, and that the next step is data (USDMA SEOC daily reports, RTI), not models.
