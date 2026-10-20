"""
WS-05.7 / V-38 (PRAHAR_MASTER_PLAN.md): more rain must never lower flood risk. Does a monotone-constrained XGBoost
keep the deployed model's skill?

Finding that motivated it: adding +20 mm to the 24/48/72 h rain sums LOWERS the deployed model's score in ~3 % of
labelled hours (worst -0.29), because nothing in the unconstrained trees forbids it.

Fixed before the run (2026-10-21):
  data        the deployed splits (src/split.py): train < 2023-07-01, validation Jul 2023, test 1-25 Aug 2023;
              the deployed 23 features (Exp_G_Static_History) and preprocessing
  models      "deployed" = the deployed hyper-parameters retrained here (must reproduce test ROC-AUC 0.708 +/- 0.005);
              "monotone" = identical, plus monotone_constraints = +1 on rain_1h..rain_72h, rain_max_intensity_24h,
              api_decay_85, discharge_clean, discharge_anomaly (every other feature unconstrained)
  checks      violation rate: share of validation + test hours whose raw score falls when 24/48/72 h rain rises by 5, 20
              and 50 mm; ROC-AUC and PR-AUC (with base rate) on validation and test
  adoption    the monotone model is recorded as the v1.0 candidate if: violation rate is 0 at every step AND test PR-AUC
              >= deployed - 0.01 AND validation PR-AUC >= deployed - 0.01. The deployed model is not replaced here:
              calibration, tiers and verification are re-run on the v1.0 protocol first.
Run: python -m src.monotone_study   ->  results/v3/v38_monotone.json, results/v3/v38_monotone.md
"""
import json

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from src.data_loader import FEATURE_EXPERIMENTS, FINAL_EXPERIMENT, load_ml_dataset
from src.model_config import RANDOM_STATE, RESULTS_DIR, TARGET_COL
from src.preprocessing import get_tree_preprocessor
from src.split import get_chronological_splits

OUT = RESULTS_DIR / "v3"
FEATS = FEATURE_EXPERIMENTS[FINAL_EXPERIMENT]
INCREASING = {"rain_1h", "rain_3h", "rain_6h", "rain_12h", "rain_24h", "rain_48h", "rain_72h", "rain_max_intensity_24h",
              "api_decay_85", "discharge_clean", "discharge_anomaly"}
PARAMS = json.loads((RESULTS_DIR / "hyperparameter_tuning/xgboost_best_params.json").read_text())


def model(monotone: bool) -> Pipeline:
    kw = {k.replace("classifier__", ""): v for k, v in PARAMS.items()}
    if monotone:
        kw["monotone_constraints"] = "(" + ",".join("1" if f in INCREASING else "0" for f in FEATS) + ")"
    return Pipeline([("preprocessor", get_tree_preprocessor()),
                     ("classifier", XGBClassifier(random_state=RANDOM_STATE, eval_metric="logloss", n_jobs=-1, **kw))])


def violations(m: Pipeline, X: pd.DataFrame) -> dict:
    p0 = m.predict_proba(X)[:, 1]
    out = {}
    for d in (5, 20, 50):
        X2 = X.copy()
        for c in ("rain_24h", "rain_48h", "rain_72h"):
            X2[c] = X2[c] + d
        p1 = m.predict_proba(X2)[:, 1]
        out[f"+{d}mm"] = {"share_lower": round(float(np.mean(p1 < p0 - 1e-9)), 4), "share_higher": round(float(np.mean(p1 > p0 + 1e-9)), 4),
                          "worst_drop": round(float(np.min(p1 - p0)), 4)}
    return out


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    tr, va, te = get_chronological_splits(load_ml_dataset())
    res = {"features": FEATS, "constrained_increasing": sorted(INCREASING), "params": PARAMS, "models": {}}
    for name, mono in (("deployed (retrained)", False), ("monotone", True)):
        m = model(mono).fit(tr[FEATS], tr[TARGET_COL].astype(int))
        r = {}
        for split, d in (("validation", va), ("test", te)):
            y, p = d[TARGET_COL].astype(int), m.predict_proba(d[FEATS])[:, 1]
            r[split] = {"roc_auc": round(float(roc_auc_score(y, p)), 4), "pr_auc": round(float(average_precision_score(y, p)), 4),
                        "base_rate": round(float(y.mean()), 4), "distinct_scores": int(np.unique(np.round(p, 8)).size)}
        r["violations"] = violations(m, pd.concat([va, te])[FEATS])
        res["models"][name] = r
    d, mo = res["models"]["deployed (retrained)"], res["models"]["monotone"]
    res["reproduces_deployed"] = abs(d["test"]["roc_auc"] - 0.708) <= 0.005
    checks = {"no_violations": all(v["share_lower"] == 0 for v in mo["violations"].values()),
              "test_pr_auc_within_0.01": mo["test"]["pr_auc"] >= d["test"]["pr_auc"] - 0.01,
              "val_pr_auc_within_0.01": mo["validation"]["pr_auc"] >= d["validation"]["pr_auc"] - 0.01}
    res["adoption"] = checks | {"candidate_for_v1": all(checks.values()) and res["reproduces_deployed"]}
    (OUT / "v38_monotone.json").write_text(json.dumps(res, indent=2), encoding="utf-8")

    rows = []
    for name, r in res["models"].items():
        rows.append({"model": name, "val ROC": r["validation"]["roc_auc"], "val PR-AUC": r["validation"]["pr_auc"],
                     "test ROC": r["test"]["roc_auc"], "test PR-AUC": r["test"]["pr_auc"], "test base rate": r["test"]["base_rate"],
                     "distinct test scores": r["test"]["distinct_scores"],
                     **{f"rain {k}: score falls": f"{v['share_lower']:.1%} (worst {v['worst_drop']:+.2f})" for k, v in r["violations"].items()}})
    md = ["# V-38: monotone rain constraints (WS-05.7)", "",
          "Question: does forcing 'more rain never lowers risk' cost skill? Same splits, features, preprocessing and hyper-parameters "
          "as the deployed XGBoost; only the monotone constraints differ. Rule fixed before the run: see `src/monotone_study.py`.", "",
          pd.DataFrame(rows).to_markdown(index=False), "",
          f"Reproduces the deployed model (test ROC-AUC 0.708 ± 0.005): **{res['reproduces_deployed']}**.", "",
          f"**Decision:** {'record the monotone model as the v1.0 candidate' if res['adoption']['candidate_for_v1'] else 'not a v1.0 candidate under the pre-set rule'} {checks}.", ""]
    (OUT / "v38_monotone.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    return res


if __name__ == "__main__":
    run()
