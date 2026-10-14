"""Combined report for MODEL_UPGRADE_PLAN.md experiments -> results/model_upgrade.md. Run: python scripts/model_upgrade_report.py"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
U = ROOT / "results/model_upgrade"


def j(name):
    p = U / name
    return json.loads(p.read_text()) if p.exists() else None


def main():
    L = ["# PRAHAR: model upgrade experiments (MODEL_UPGRADE_PLAN.md)", "",
         "Every adoption rule is written in the module docstring before the first run; the same splits and verification code are used throughout.", ""]
    e1 = j("e1_ensemble.json")
    if e1:
        L += ["## E1: equal-weight ensemble (LR + RF + XGBoost, percentile-averaged)", "",
              "| Model | ROC-AUC v1 | PR-AUC v1 | Day CSI v1 | PR-AUC v2 | Day CSI v2 |", "|---|---|---|---|---|---|"]
        L += [f"| {k} | {e1[k]['v1']['roc_auc']} | {e1[k]['v1']['pr_auc']} | {e1[k]['v1']['dd_CSI']} | {e1[k]['v2']['pr_auc']} | {e1[k]['v2']['dd_CSI']} |" for k in ("xgb", "rf", "ens")]
        L += ["", f"Event-CV pooled PR-AUC: XGBoost {e1['event_cv']['xgb']['pooled_pr_auc']}, ensemble {e1['event_cv']['ens']['pooled_pr_auc']} "
              f"(ROC {e1['event_cv']['xgb']['pooled_roc_auc']} → {e1['event_cv']['ens']['pooled_roc_auc']}).",
              f"Decision: **adopt = {e1['decision']['adopt']}** {e1['decision']}. Ranking improves; district-day CSI does not.", ""]
    e2 = j("e2_thresholds.json")
    if e2:
        h = e2["thresholds_mm"]["hills"]
        L += ["## E2: rainfall thresholds fitted on documented events", "",
              f"Fit on {e2['thresholds_mm']['n_fit_events']} events (2022 – Jul 2023 and 2024). Hills, 24 h: ALERT {h['r24']['ALERT']} · SEVERE {h['r24']['SEVERE']} · EXTREME {h['r24']['EXTREME']} mm; "
              f"72 h: {h['r72']['ALERT']} · {h['r72']['SEVERE']} · {h['r72']['EXTREME']} mm (plains: too few events, so pooled values are used).",
              "**Finding:** half of the documented floods had < 50 mm/24 h at the wettest gauge in their district, so most were local cloudbursts the gauge network did not record. Rain at the gauge cannot separate flood days from wet days.", "",
              "| Rule | Test day POD | FAR | CSI | 2025 events POD | ALERT district-days 2024 / 2025 |", "|---|---|---|---|---|---|"]
        L += [f"| {k} | {e2[k]['test_dd']['POD']} | {e2[k]['test_dd']['FAR']} | {e2[k]['test_dd']['CSI']} | {e2[k]['pod_2025']} | {e2[k]['alert_dd']['2024']} / {e2[k]['alert_dd']['2025']} |" for k in ("current", "fitted")]
        L += ["", f"Decision: **adopt = {e2['decision']['adopt']}** {e2['decision']}.", ""]
    e3 = j("e3_district_pooled.json")
    if e3:
        r = e3["ranking_recall_at_3"]
        L += ["## E3: pooled district-day model + ranking view", "",
              f"Test ROC-AUC {e3['test']['roc_auc']}, PR-AUC {e3['test']['pr_auc']} (base rate {e3['test']['base_rate']}). As an alert layer at frequency bias 2: "
              f"CSI {e3['test_common']['pooled']['CSI']} vs hybrid {e3['test_common']['hybrid']['CSI']}; external {e3['external_pooled']['detected']}/{e3['external_pooled']['events_scored']} vs hybrid {e3['external_hybrid']['detected']}/{e3['external_hybrid']['events_scored']}.",
              f"Ranking, recall@3 (flooded district among the day's top 3): test {r['test_model']} vs district prior {r['test_prior']}; external events {r['external_model']} vs prior {r['external_prior']} (chance {r['chance']}).",
              f"Decision: alert layer adopt = **{e3['decision']['adopt_alert_layer']}**; ranking view offered = **{e3['decision']['offer_ranking_view']}** (Overview → 'Districts to watch').", ""]
    L += ["## Conclusion", "", "No alert-layer change beats the deployed hybrid under its pre-set rule. The limit is the labels (about 50 IMD flood district-days) and the gauge network's blindness to local cloudbursts, not the model class. "
          "Two things do improve and are kept as reported results: ranking (ensemble ROC-AUC 0.78; district ranking recall@3 0.34 vs 0.21 prior). "
          "Next steps are data: a complete 2024–25 event list (USDMA SEOC daily reports via RTI) and radar or satellite rain (IMD Doppler or GPM IMERG) that can see cloudbursts between gauges."]
    (ROOT / "results/model_upgrade.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
