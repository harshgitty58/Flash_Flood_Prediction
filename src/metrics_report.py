"""
Consolidated accuracy metrics (hour level, event level, warning level).

  results/metrics/metrics_summary.csv   one row per model × split at the frozen threshold
  results/metrics/confusion_matrices.json
  results/metrics/metrics.json          everything the frontend Metrics page needs
  results/metrics/pr_curve_xgboost.csv  precision/recall/F1 vs threshold (test) for the threshold slider
Run: python -m src.metrics_report   (after training, event CV and warning levels)
"""
import json

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, precision_recall_curve

from src.evaluate import compute_all_metrics
from src.model_config import EVALUATION_DIR, RESULTS_DIR, TARGET_COL

OUT = RESULTS_DIR / "metrics"
MODELS = ["logistic_regression", "random_forest", "xgboost"]


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    cmp_ = pd.read_csv(RESULTS_DIR / "model_evaluation" / "model_comparison.csv")
    thr = dict(zip(cmp_["model"].str.lower().str.replace(" ", "_"), cmp_["threshold"]))
    rows, cms = [], {}
    for m in MODELS:
        for split in ("validation", "test"):
            p = pd.read_csv(RESULTS_DIR / "predictions" / f"{split}_{m}.csv")
            y, s = p[TARGET_COL].astype(int).to_numpy(), p["predicted_probability"].to_numpy()
            met = compute_all_metrics(y, s, threshold=float(thr[m]))
            tn, fp, fn, tp = confusion_matrix(y, (s >= thr[m]).astype(int), labels=[0, 1]).ravel()
            months = max(1.0, (pd.to_datetime(p["datetime"]).max() - pd.to_datetime(p["datetime"]).min()).days / 30.4)
            met.update({"model": m, "split": split, "threshold": float(thr[m]), "rows": len(p), "positives": int(y.sum()),
                        "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
                        "false_alarms_per_station_month": round(fp / max(1, p["station"].nunique()) / months, 2)})
            rows.append(met)
            cms[f"{m}_{split}"] = [[int(tn), int(fp)], [int(fn), int(tp)]]
    summ = pd.DataFrame(rows)
    lead = ["model", "split", "threshold", "rows", "positives", "precision", "recall", "f1", "specificity",
            "balanced_accuracy", "mcc", "roc_auc", "pr_auc", "brier", "tp", "fp", "fn", "tn", "false_alarms_per_station_month"]
    summ = summ[[c for c in lead if c in summ] + [c for c in summ if c not in lead]]
    summ.to_csv(OUT / "metrics_summary.csv", index=False)
    (OUT / "confusion_matrices.json").write_text(json.dumps(cms, indent=2))

    # precision / recall / F1 across thresholds (deployed XGBoost, calibrated test probabilities)
    t = pd.read_csv(RESULTS_DIR / "conformal" / "cp_test_predictions.csv")
    pr, rc, th = precision_recall_curve(t[TARGET_COL].astype(int), t["p_calibrated"])
    curve = pd.DataFrame({"threshold": th, "precision": pr[:-1], "recall": rc[:-1]})
    curve["f1"] = 2 * curve.precision * curve.recall / (curve.precision + curve.recall).replace(0, np.nan)
    curve = curve.iloc[np.unique(np.linspace(0, len(curve) - 1, 120).astype(int))].round(4)
    curve.to_csv(OUT / "pr_curve_xgboost.csv", index=False)

    ev = pd.read_csv(RESULTS_DIR / "event_cv" / "event_cv_summary.csv")
    lead_s = json.loads((RESULTS_DIR / "event_cv" / "event_lead_summary.json").read_text())
    events = pd.read_csv(RESULTS_DIR / "event_cv" / "event_lead_times.csv")
    warn = json.loads((RESULTS_DIR / "warning_levels" / "warning_thresholds.json").read_text())
    out = {"hour_level": summ.to_dict("records"), "confusion": cms, "pr_curve": curve.to_dict("records"),
           "event_cv": ev.to_dict("records"), "event_detection": lead_s, "events": events.astype(object).where(events.notna(), None).to_dict("records"),
           "warning_levels": warn.get("alert_level", {}), "splits": json.loads((RESULTS_DIR / "splits.json").read_text())}
    ver = RESULTS_DIR / "verification" / "verification.json"
    if ver.exists():
        v = json.loads(ver.read_text())
        out["verification"] = {k: v[k] for k in ("contingency", "probabilistic", "lead_time", "relative_value", "breakdown_district")}
    ext = RESULTS_DIR / "metrics" / "external_validation.json"
    if ext.exists():
        out["external_validation"] = json.loads(ext.read_text())
    out["labels"] = labels_block()
    def strict(o):  # bare NaN/inf is not valid JSON for browsers
        if isinstance(o, float) and not np.isfinite(o):
            return None
        return {k: strict(v) for k, v in o.items()} if isinstance(o, dict) else [strict(v) for v in o] if isinstance(o, list) else o
    (OUT / "metrics.json").write_text(json.dumps(strict(json.loads(json.dumps(out, default=str))), indent=2, allow_nan=False))
    print(summ[["model", "split", "precision", "recall", "f1", "mcc", "roc_auc", "pr_auc", "tp", "fp", "fn"]].to_string(index=False))
    return out


def labels_block() -> dict:
    """Ground-truth section (LABELS_PLAN.md): label sources, IMD vs SANDRP audit, v1/v2 experiment, before/after."""
    from src.config import PROJECT_ROOT
    lab, L = {}, RESULTS_DIR / "labels"
    if (PROJECT_ROOT / "data/external/labels/labels_summary.json").exists():
        lab["sources"] = json.loads((PROJECT_ROOT / "data/external/labels/labels_summary.json").read_text())
    if (L / "label_audit.json").exists():
        lab["audit"] = json.loads((L / "label_audit.json").read_text())
    if (L / "label_experiment.json").exists():
        e = json.loads((L / "label_experiment.json").read_text())
        keep = ("trained_on", "scored_on", "pr_auc", "roc_auc", "f1", "dd_POD", "dd_FAR", "dd_CSI", "dd_CSI_ci95")
        lab["experiment"] = {"decision": e["decision"], "event_cv": e["event_cv"],
                             "xgboost_grid": [{k: g[k] for k in keep} for g in e["grid"] if g["model"] == "XGBoost"]}
    b0 = RESULTS_DIR / "baseline_v0" / "model_evaluation" / "model_comparison.csv"
    if b0.exists():
        cols = ["test_roc_auc", "test_pr_auc", "test_f1", "test_mcc"]
        a = pd.read_csv(b0).set_index("model")[cols]
        b = pd.read_csv(EVALUATION_DIR / "model_comparison.csv").set_index("model")[cols]
        lab["before_after"] = [{"model": m, **{f"{c[5:]}_before": round(float(a.loc[m, c]), 4) for c in cols},
                                **{f"{c[5:]}_after": round(float(b.loc[m, c]), 4) for c in cols}} for m in b.index if m in a.index]
    dd = RESULTS_DIR / "district_day" / "summary.json"
    if dd.exists():
        x = json.loads(dd.read_text())
        lab["district_day"] = {"model": x["model"], "test_roc_auc": x["test_all"]["roc_auc"], "test_pr_auc": x["test_all"]["pr_auc"],
                               "base_rate": x["test_all"]["base_rate"], "csi": x["test_common_with_hybrid"]["district_day_model"]["CSI"],
                               "hybrid_csi": x["test_common_with_hybrid"]["hybrid"]["CSI"], "external": f"{x['external_district_day_model']['detected']}/{x['external_district_day_model']['events_scored']}",
                               "adopted": x["decision"]["adopt"]}
    up = RESULTS_DIR / "model_upgrade"
    if (up / "e1_ensemble.json").exists() and (up / "e2_thresholds.json").exists() and (up / "e3_district_pooled.json").exists():
        e1, e2, e3 = (json.loads((up / f).read_text()) for f in ("e1_ensemble.json", "e2_thresholds.json", "e3_district_pooled.json"))
        lab["model_upgrade"] = {"e1": {"roc_xgb": e1["xgb"]["v1"]["roc_auc"], "roc_ens": e1["ens"]["v1"]["roc_auc"], "adopt": e1["decision"]["adopt"]},
                                "e2": {"csi_current": e2["current"]["test_dd"]["CSI"], "csi_fitted": e2["fitted"]["test_dd"]["CSI"],
                                       "median_event_24h": e2["thresholds_mm"]["hills"]["r24"]["SEVERE"], "adopt": e2["decision"]["adopt"]},
                                "e3": {**e3["ranking_recall_at_3"], "ranking": e3["decision"]["offer_ranking_view"]}}
    rr = RESULTS_DIR / "warning_levels" / "rain_rule.json"
    if rr.exists():
        r = json.loads(rr.read_text())
        lab["rain_rule_tuning"] = {k: r.get(k) for k in ("rule", "adopted", "best_candidate", "adoption_rule")}
    return lab


if __name__ == "__main__":
    run()
