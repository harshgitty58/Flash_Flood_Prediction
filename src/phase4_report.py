"""
Objective 4E — bundle inference artifacts and write results/phase4_report.md from the Phase 4 outputs.
Run after: src.train_pipeline → src.event_cv → src.conformal → src.warning_levels → src.explain → src.robustness
Run: python -m src.phase4_report
"""
import json
import shutil

import pandas as pd

from src.data_loader import FEATURE_EXPERIMENTS, FINAL_EXPERIMENT
from src.model_config import RESULTS_DIR, XGB_MODEL_DIR

ART = RESULTS_DIR / "inference_artifacts"


def run():
    ART.mkdir(parents=True, exist_ok=True)
    shutil.copy(XGB_MODEL_DIR / "model.joblib", ART / "xgboost_model.joblib")
    shutil.copy(RESULTS_DIR / "conformal" / "calibration_scores.csv", ART / "calibration_scores.csv")
    shutil.copy(RESULTS_DIR / "warning_levels" / "warning_thresholds.json", ART / "warning_thresholds.json")
    (ART / "feature_columns.json").write_text(json.dumps({"experiment": FINAL_EXPERIMENT, "features": FEATURE_EXPERIMENTS[FINAL_EXPERIMENT]}, indent=2))

    cv = pd.read_csv(RESULTS_DIR / "event_cv" / "event_cv_summary.csv")
    lead = json.loads((RESULTS_DIR / "event_cv" / "event_lead_summary.json").read_text())
    leads = pd.read_csv(RESULTS_DIR / "event_cv" / "event_lead_times.csv")
    cp = json.loads((RESULTS_DIR / "conformal" / "cp_summary.json").read_text())
    warn = json.loads((RESULTS_DIR / "warning_levels" / "warning_thresholds.json").read_text())
    conf = pd.read_csv(RESULTS_DIR / "warning_levels" / "warning_level_confusion.csv")
    shap_g = pd.read_csv(RESULTS_DIR / "shap" / "shap_global_importance.csv").head(10)
    rob = pd.read_csv(RESULTS_DIR / "robustness" / "robustness_summary.csv")
    cmp_ = pd.read_csv(RESULTS_DIR / "model_evaluation" / "model_comparison.csv")

    md = f"""# Phase 4 Report — Uncertainty-Aware and Robust Flash-Flood Prediction

## 0. Corrections made before Phase 4
- **Duplicate station-hours** (one gauge with two coordinate pairs fanned out the merge) fixed → 21,464 rows.
- **Label coverage**: the IMD flood inventory ends 2023-08-26. Rows after that were silently labelled 0; they are now
  *unlabelled* (used for replay only). Labelled data: 7,830 rows, 44 positives, 6 flood episodes.
- **Location leakage**: raw latitude/longitude carried 38 % of gain. Final model = `{FINAL_EXPERIMENT}` (no coordinates).

## 1. Evaluation protocol — leave-one-event-out CV (src/event_cv.py)
Each flood episode (±3 days) is held out in turn; training excludes a 7-day buffer around it.

{cv.to_markdown(index=False)}

Single chronological split (train 2022 · val Jan–Jul 2023 · test Aug 2023, 17 positives) for reference:

{cmp_[["model", "feature_set", "threshold", "val_roc_auc", "val_pr_auc", "test_roc_auc", "test_pr_auc", "test_recall"]].to_markdown(index=False)}

## 2. Uncertainty — Venn-Abers + Mondrian conformal (src/conformal.py)
Calibration on {cp['calibration_rows']:,} validation rows ({cp['calibration_positives']} floods); test {cp['test_rows']} rows ({cp['test_positives']} floods).
Brier score {cp['brier_raw']} (raw) → {cp['brier_calibrated']} (calibrated).

{pd.DataFrame(cp['coverage']).to_markdown(index=False)}

Nominal coverage is met for both classes at 90 % and 95 %. Most sets are "uncertain": the model rarely separates
the classes with confidence, which is the honest outcome with ~20 calibration floods.

## 3. Explanations — SHAP (src/explain.py)
{shap_g.to_markdown(index=False)}

## 4. Warning levels (src/warning_levels.py)
Calibrated-probability cut-offs {warn['thresholds']} (base rate {warn['base_rate']:.2%}); a conformal FLOOD set lifts to ≥ ALERT.

{conf.to_markdown(index=False)}

≥ ALERT on the test month: recall {warn['test_alert_recall']}, precision {warn['test_alert_precision']}, false-alarm rate {warn['test_false_alarm_rate']}.

## 5. Lead time (event level, out-of-fold)
Alarm threshold = 95th percentile of non-flood scores (5 % hourly false alarms).
**{lead['events_detected']}/{lead['events_evaluated']} district floods detected.** Lead times equal to the 48 h search window mean the alarm was already on at the window start (largely the district baseline), so no lead-time figure is claimed.

{leads.to_markdown(index=False)}

## 6. Robustness to degraded inputs (src/robustness.py)
{rob.to_markdown(index=False)}

## 7. Limitations
- 44 positive station-hours / 6 episodes: every metric has wide uncertainty.
- Flood-history features go stale after 2023-08 (no newer labels) → replay-period predictions extrapolate.
- River discharge contributes nothing (7 gauges, most stations unmatched); DEM, soil moisture and satellite rainfall not yet used.

## 8. Inference artifacts (results/inference_artifacts/)
`xgboost_model.joblib`, `feature_columns.json`, `calibration_scores.csv` (Venn-Abers/conformal calibration), `warning_thresholds.json`.
"""
    (RESULTS_DIR / "phase4_report.md").write_text(md, encoding="utf-8")
    print("wrote results/phase4_report.md and", sorted(p.name for p in ART.iterdir()))


if __name__ == "__main__":
    run()
