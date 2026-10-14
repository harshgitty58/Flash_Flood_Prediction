"""Before/after report for the label work (LABELS_PLAN.md §0 reporting rule) -> results/label_impact.md

Compares the frozen baseline (results/baseline_v0/, saved before the L0 district-name fix) with the current results,
on identical splits, features and verification code; appends the label v1/v2 experiment and the label audit.
Run: python scripts/label_impact_report.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
R, B = ROOT / "results", ROOT / "results/baseline_v0"


def table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join("" if not isinstance(v, (list, tuple)) and pd.isna(v) else str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join(out)


def model_cmp() -> str:
    keep = ["model", "test_roc_auc", "test_pr_auc", "test_precision", "test_recall", "test_f1", "test_mcc", "test_brier"]
    a = pd.read_csv(B / "model_evaluation/model_comparison.csv")[keep].set_index("model")
    b = pd.read_csv(R / "model_evaluation/model_comparison.csv")[keep].set_index("model")
    rows = []
    for m in b.index:
        rows.append({"model": m, **{k.replace("test_", ""): f"{a.loc[m, k]:.3f} → **{b.loc[m, k]:.3f}**" for k in keep[1:]}})
    return table(pd.DataFrame(rows))


def contingency_cmp() -> str:
    a, b = pd.read_csv(B / "verification/contingency_scores.csv"), pd.read_csv(R / "verification/contingency_scores.csv")
    key = ["unit", "split", "level", "layer"]
    m = a.merge(b, on=key, suffixes=("_v0", "_now"))
    m = m[(m["split"] == "test") & (m["level"] == "≥ ALERT")]
    rows = [{"unit": r.unit, "layer": r.layer, "events": f"{r.events_v0} → {r.events_now}",
             **{s: f"{getattr(r, s + '_v0'):.3f} → **{getattr(r, s + '_now'):.3f}**" for s in ("POD", "FAR", "CSI", "HSS")}}
            for r in m.itertuples()]
    return table(pd.DataFrame(rows))


def main():
    sv0 = json.loads((B / "metrics/metrics.json").read_text()).get("splits") if (B / "metrics/metrics.json").exists() else None
    sp = json.loads((R / "splits.json").read_text())
    lines = ["# PRAHAR: label work, before and after", "",
             "Baseline v0 was frozen before any label change (`results/baseline_v0/`). Every number below uses the same "
             "splits, the same 23 features (Exp_G), the same tuning search and the same verification code; only the labels differ.", "",
             "## L0: district-name fix in the label join", "",
             "The IMD inventory spells *Rudra Prayag*, *Udam Singh Nagar* and *Garhwal* (the Census name of Pauri Garhwal), while the "
             "station table spells *Rudraprayag*, *Udham Singh Nagar* and *Pauri Garhwal*. The label join is an exact string match, "
             "so 13 of the 29 IMD event-days in 2022–23 were silently scored as 'no flood'. Rudraprayag, the most flood-hit district "
             "in the window, had 0 positives.", "",
             "| split | positives (station-hours) now |", "|---|---|"]
    lines += [f"| {k} | {v['positives']} of {v['rows']:,} |" for k, v in sp.items() if isinstance(v, dict) and "positives" in v]
    lines += ["", "Before L0, the positives were 271 (train), 384 (validation) and 240 (test).", "",
              "### Held-out test (Aug 2023), station-hour", "", model_cmp(), "",
              "### Verification at ≥ ALERT on the test month (WMO categorical scores)", "", contingency_cmp(), ""]
    ecv = pd.read_csv(R / "event_cv/event_cv_summary.csv")
    lines += ["### Leave-one-event-out CV (XGBoost)", "", table(ecv[["experiment", "folds", "positives", "pooled_roc_auc", "pooled_pr_auc", "base_rate", "min_fold_roc_auc"]]), "",
              "Before L0, Exp_G scored a pooled ROC-AUC of 0.858 on event-CV. That number was inflated: all positives came from 5 districts, "
              "so the static district features could pick out 'the districts that have labels'. After the fix, event-CV (0.70) and the held-out "
              "test (0.71) agree. Exp_C/D score higher on event-CV, but they rely on the IMD flood-history features, which stop updating "
              "when the inventory ends (2023-08). They cannot be deployed for 2024+, so Exp_G stays the deployed set.", ""]

    la = R / "labels/label_audit.json"
    if la.exists():
        s = json.loads(la.read_text())["summary"]
        lines += ["## Label audit: IMD vs SANDRP (2022 – Aug 2023)", "",
                  f"- IMD events {s['imd_events']}, SANDRP events {s['sandrp_events']}; IMD days also reported by SANDRP: {s['imd_days_confirmed_by_sandrp']}/{s['imd_district_days']}.",
                  f"- **SANDRP-only events: {s['sandrp_only_events']}**, i.e. damaging events that are missing from the training labels "
                  f"(by split: {s['sandrp_only_by_split']}). On {s['sandrp_only_valtest_alerted_by_hybrid']} of the validation/test SANDRP-only days the deployed hybrid already alerted, "
                  "and v1 scores those alerts as false alarms.",
                  f"- Decision gate ({s['gate']['rule']}): share {s['gate']['share']}, passed = **{s['gate']['passed']}**.", ""]
    le = R / "labels/label_experiment.json"
    if le.exists():
        e = json.loads(le.read_text())
        g = pd.DataFrame(e["grid"])
        g = g[g["model"] == "XGBoost"][["trained_on", "scored_on", "threshold", "roc_auc", "pr_auc", "precision", "recall", "f1", "test_base_rate", "dd_POD", "dd_FAR", "dd_CSI", "dd_CSI_ci95"]]
        lines += ["## Label v2 experiment (XGBoost; 2×2 train-label × truth grid)", "", table(g), "",
                  "Event-CV with each version's own truth:", "", table(pd.DataFrame(e["event_cv"]).T.reset_index(names="labels")), "",
                  f"Decision rule: {e['decision']['rule']}.", "",
                  f"Result: v2 on v1 truth ok = {e['decision']['v2_on_v1_truth_ok']}, v2 on v2 truth ok = {e['decision']['v2_on_v2_truth_ok']}, "
                  f"event-CV ok = {e['decision']['event_cv_ok']}, so **adopt v2 = {e['decision']['adopt_v2']}**.", ""]
    xv = R / "metrics/external_validation.json"
    if xv.exists():
        s = json.loads(xv.read_text())["summary"]
        lines += ["## External validation (events after the training labels end)", "",
                  f"- {s['events']} documented events ({s['period']}); {s['events_with_station_data']} had a reporting gauge in the district.",
                  f"- Hybrid ≥ ALERT POD: {s['pod_hybrid_alert']['detected']}/{s['pod_hybrid_alert']['n']} = {s['pod_hybrid_alert']['POD']} (95 % CI {s['pod_hybrid_alert']['ci95']}); "
                  f"ML-only {s['pod_ml_alert']['POD']}; rainfall-only {s['pod_rain_alert']['POD']}.",
                  "- Alert burden (ALERT+ district-days per monsoon; share within ±2 days of a documented event): "
                  + "; ".join(f"{a['monsoon']}: {a['alert_district_days']} ({a['share_near_event']:.0%})" for a in s["alert_burden"]), ""]
    (R / "label_impact.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
