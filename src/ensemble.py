"""
E1 (MODEL_UPGRADE_PLAN.md) — equal-weight ensemble of Logistic Regression, Random Forest and XGBoost.

The three models are calibrated very differently (XGBoost is trained with scale_pos_weight ≈ 255), so raw
probabilities are not averaged: each model's score is mapped to its percentile within a reference score
distribution (validation scores for the test run; the training fold's scores inside event-CV), and the three
percentiles are averaged with equal weights. No weights or extra parameters are tuned.
Threshold: same rule as the deployed model (src.evaluate.find_optimal_threshold on validation).
XGBoost alone is re-scored with exactly the same code, so the comparison is like for like.

Adoption rule (fixed before the run): adopt if the ensemble's event-CV pooled PR-AUC ≥ XGBoost's AND on the test
month its PR-AUC and district-day CSI are ≥ XGBoost's on BOTH answer keys (v1 IMD, v2 IMD+SANDRP+SitReps).
Output: results/model_upgrade/e1_ensemble.json
Run: python -m src.ensemble
"""
import json

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from src.data_loader import FEATURE_EXPERIMENTS, FINAL_EXPERIMENT, load_ml_dataset
from src.data_window import STUDY_START
from src.evaluate import compute_all_metrics, find_optimal_threshold
from src.event_cv import BUFFER_DAYS, MERGE_DAYS, WINDOW_DAYS
from src.label_experiment import MODELS, build_labels, district_day, model
from src.model_config import RESULTS_DIR, TARGET_COL, TRAIN_END_DATE, VAL_END_DATE

OUT = RESULTS_DIR / "model_upgrade"
FEATS = FEATURE_EXPERIMENTS[FINAL_EXPERIMENT]


def fit_all(df: pd.DataFrame, y: str) -> dict:
    return {n: model(n, df[y]).fit(df[FEATS], df[y].astype(int)) for n in MODELS}


def scores(ms: dict, X: pd.DataFrame) -> dict:
    return {n: m.predict_proba(X)[:, 1] for n, m in ms.items()}


def ensemble(s: dict, ref: dict) -> np.ndarray:
    """Mean of each model's percentile within its reference scores."""
    return np.mean([np.searchsorted(np.sort(ref[n]), s[n], side="right") / len(ref[n]) for n in s], axis=0)


def event_cv(df: pd.DataFrame) -> dict:
    d = df.reset_index(drop=True)
    days = sorted(d.loc[d[TARGET_COL] == 1, "datetime"].dt.normalize().unique())
    eps = []
    for x in days:
        (eps[-1].append(x) if eps and (x - eps[-1][-1]).days <= MERGE_DAYS else eps.append([x]))
    P = []
    for e in eps:
        c = pd.Timestamp(e[0]) + (pd.Timestamp(e[-1]) - pd.Timestamp(e[0])) / 2
        gap = (d["datetime"] - c).abs()
        te, tr = d[gap <= pd.Timedelta(days=WINDOW_DAYS)], d[gap > pd.Timedelta(days=BUFFER_DAYS)]
        if tr[TARGET_COL].sum() == 0 or te[TARGET_COL].nunique() < 2:
            continue
        ms = fit_all(tr, TARGET_COL)
        s_te, s_tr = scores(ms, te[FEATS]), scores(ms, tr[FEATS])
        P.append(pd.DataFrame({"y": te[TARGET_COL].to_numpy(), "xgb": s_te["XGBoost"], "ens": ensemble(s_te, s_tr)}))
    P = pd.concat(P)
    return {k: {"pooled_roc_auc": round(roc_auc_score(P["y"], P[k]), 4), "pooled_pr_auc": round(average_precision_score(P["y"], P[k]), 4)}
            for k in ("xgb", "ens")} | {"folds": len(eps)}


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    df = load_ml_dataset()
    df = build_labels(df[df[TARGET_COL].notna() & (df["datetime"] >= STUDY_START)].reset_index(drop=True))
    tr = df[df["datetime"] < pd.Timestamp(TRAIN_END_DATE)]
    va = df[(df["datetime"] >= pd.Timestamp(TRAIN_END_DATE)) & (df["datetime"] < pd.Timestamp(VAL_END_DATE))]
    te = df[df["datetime"] >= pd.Timestamp(VAL_END_DATE)]
    ms = fit_all(tr, "y_v1")
    s_va, s_te = scores(ms, va[FEATS]), scores(ms, te[FEATS])
    cand = {"xgb": (s_va["XGBoost"], s_te["XGBoost"]), "ens": (ensemble(s_va, s_va), ensemble(s_te, s_va)),
            "rf": (s_va["Random Forest"], s_te["Random Forest"])}
    res = {}
    for k, (pv, pt) in cand.items():
        thr, _ = find_optimal_threshold(va["y_v1"].astype(int).to_numpy(), pv)
        res[k] = {"threshold": thr}
        for truth in ("y_v1", "y_v2"):
            yt = te[truth].astype(int).to_numpy()
            sh = compute_all_metrics(yt, pt, threshold=thr)
            dd = district_day(te, pt, thr, truth)
            res[k][truth[2:]] = {"roc_auc": round(sh["roc_auc"], 4), "pr_auc": round(sh["pr_auc"], 4), "f1": round(sh["f1"], 4),
                                 "precision": round(sh["precision"], 4), "recall": round(sh["recall"], 4),
                                 "dd_POD": dd["POD"], "dd_FAR": dd["FAR"], "dd_CSI": dd["CSI"], "dd_CSI_ci95": dd["ci95"]["CSI"]}
    res["event_cv"] = event_cv(df[df[TARGET_COL].notna()])
    e, x = res["ens"], res["xgb"]
    ok = lambda k, t: (e[t][k] or 0) >= (x[t][k] or 0)  # noqa: E731
    res["decision"] = {"event_cv_ok": res["event_cv"]["ens"]["pooled_pr_auc"] >= res["event_cv"]["xgb"]["pooled_pr_auc"],
                       "test_v1_ok": ok("pr_auc", "v1") and ok("dd_CSI", "v1"), "test_v2_ok": ok("pr_auc", "v2") and ok("dd_CSI", "v2")}
    res["decision"]["adopt"] = all(res["decision"].values())
    (OUT / "e1_ensemble.json").write_text(json.dumps(res, indent=2, default=str))
    for k in ("xgb", "ens", "rf"):
        print(k, {t: {m: res[k][t][m] for m in ("roc_auc", "pr_auc", "f1", "dd_POD", "dd_FAR", "dd_CSI")} for t in ("v1", "v2")})
    print(res["event_cv"], res["decision"])
    return res


if __name__ == "__main__":
    run()
