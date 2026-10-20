"""
RQ4 / WS-07.2-07.3 (PRAHAR_MASTER_PLAN.md): which calibrator and conformal setup for the deployed XGBoost scores?

Fixed before the run (2026-10-21), so the result cannot steer the rule:
  data         calibrate on the validation month (Jul 2023, results/predictions/validation_xgboost.csv),
               evaluate on the held-out test month (Aug 2023, test_xgboost.csv). Same raw scores as deployed.
  candidates   raw score (no calibration) · Platt (logistic on logit score) · beta calibration (Kull et al. 2017,
               logistic on ln s and -ln(1-s)) · isotonic · IVAP Venn-Abers (deployed) · CVAP (cross Venn-Abers, 5 folds,
               Vovk et al. 2015; geometric-mean merge of p0/p1)
  metrics      log-loss, Brier, ECE (10 equal-mass bins), distinct calibrated values, ROC-AUC (ties only);
               Mondrian conformal sets at 80/90/95 % built on each calibrator's calibration-set probabilities:
               coverage per class, singleton share, nesting (80 ⊆ 90 ⊆ 95)
  adoption     a candidate replaces IVAP only if, on the test month, ALL hold: log-loss at least 1 % lower than IVAP,
               ECE <= 0.02, >= 50 distinct calibrated values, 90 % conformal coverage >= 0.88 for each class.
               Even then the deployed model is NOT changed here: the result is recorded for v1.0, where the decision is
               re-checked on the multi-year protocol P-2 (WS-06) before any change reaches the app.
Run: python -m src.calibration_study   ->  results/v3/rq4_calibration.json, results/v3/rq4_calibration.md
"""
import json

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from src.conformal import mondrian_pvalues, venn_abers
from src.model_config import RANDOM_STATE, RESULTS_DIR, TARGET_COL
from src.params import P

OUT = RESULTS_DIR / "v3"
ALPHAS = tuple(P["conformal"]["alphas"])
EPS = 1e-6


def _logit(s):
    s = np.clip(s, EPS, 1 - EPS)
    return np.log(s / (1 - s))


def platt(cs, cy):
    m = LogisticRegression(C=1e6).fit(_logit(cs)[:, None], cy)
    return lambda s: m.predict_proba(_logit(s)[:, None])[:, 1]


def beta_cal(cs, cy):
    f = lambda s: np.column_stack([np.log(np.clip(s, EPS, 1)), -np.log(np.clip(1 - s, EPS, 1))])  # noqa: E731
    m = LogisticRegression(C=1e6).fit(f(cs), cy)
    return lambda s: m.predict_proba(f(s))[:, 1]


def isotonic(cs, cy):
    m = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip").fit(cs, cy)
    return lambda s: np.clip(m.predict(s), EPS, 1 - EPS)


def ivap(cs, cy):
    def f(s):
        p0, p1 = venn_abers(cs, cy, s)
        return p1 / (1 - p0 + p1)
    return f


def cvap(cs, cy, k=5):
    rng = np.random.default_rng(RANDOM_STATE)
    fold = rng.integers(0, k, len(cs))

    def f(s):
        p0s, p1s = [], []
        for i in range(k):
            m = fold != i
            p0, p1 = venn_abers(cs[m], cy[m], s)
            p0s.append(p0); p1s.append(p1)
        g1 = np.exp(np.mean(np.log(np.clip(p1s, EPS, 1)), 0))
        g0 = np.exp(np.mean(np.log(np.clip(1 - np.array(p0s), EPS, 1)), 0))
        return g1 / (g0 + g1)
    return f


CANDIDATES = {"raw": None, "platt": platt, "beta": beta_cal, "isotonic": isotonic, "ivap (deployed)": ivap, "cvap": cvap}


def ece(p, y, bins=10):
    edges = np.unique(np.quantile(p, np.linspace(0, 1, bins + 1)))
    idx = np.clip(np.searchsorted(edges, p, side="right") - 1, 0, len(edges) - 2)
    return float(sum(abs(y[idx == b].mean() - p[idx == b].mean()) * (idx == b).mean() for b in range(len(edges) - 1) if (idx == b).any()))


def conformal(cal_p, cal_y, p, y):
    pv = mondrian_pvalues(cal_p, cal_y, p)
    out, sets = {}, {}
    for a in ALPHAS:
        inc0, inc1 = pv[:, 0] > a, pv[:, 1] > a
        sets[a] = (inc0, inc1)
        cov = np.where(y == 1, inc1, inc0)
        out[f"{int(round((1 - a) * 100))}"] = {"coverage": round(float(cov.mean()), 4), "coverage_flood": round(float(cov[y == 1].mean()), 4),
                                               "coverage_no_flood": round(float(cov[y == 0].mean()), 4),
                                               "singleton_share": round(float((inc0 ^ inc1).mean()), 4)}
    a80, a90, a95 = sorted(ALPHAS, reverse=True)
    nested = all(((sets[a80][c] <= sets[a90][c]) & (sets[a90][c] <= sets[a95][c])).all() for c in (0, 1))
    distinct = len({(round(out[k]["coverage"], 4), out[k]["singleton_share"]) for k in out}) == len(out)
    return out | {"nested": bool(nested), "levels_distinct": bool(distinct)}


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    cal = pd.read_csv(RESULTS_DIR / "predictions/validation_xgboost.csv")
    test = pd.read_csv(RESULTS_DIR / "predictions/test_xgboost.csv")
    cs, cy = cal["predicted_probability"].to_numpy(), cal[TARGET_COL].astype(int).to_numpy()
    ts, ty = test["predicted_probability"].to_numpy(), test[TARGET_COL].astype(int).to_numpy()
    res = {"calibration_rows": int(len(cs)), "calibration_positives": int(cy.sum()), "test_rows": int(len(ts)), "test_positives": int(ty.sum()),
           "raw_distinct_scores_test": int(np.unique(ts.round(8)).size), "raw_top_score_share_test": round(float(pd.Series(ts.round(8)).value_counts(normalize=True).iloc[0]), 3),
           "candidates": {}}
    for name, fit in CANDIDATES.items():
        f = (lambda s: np.clip(s, EPS, 1 - EPS)) if fit is None else fit(cs, cy)
        pt, pc = f(ts), f(cs)
        res["candidates"][name] = {"log_loss": round(float(log_loss(ty, pt)), 5), "brier": round(float(brier_score_loss(ty, pt)), 5),
                                   "ece": round(ece(pt, ty), 4), "distinct_values": int(np.unique(np.round(pt, 8)).size),
                                   "roc_auc": round(float(roc_auc_score(ty, pt)), 4), "mean_p": round(float(pt.mean()), 4),
                                   "conformal": conformal(pc, cy, pt, ty)}
    base = res["candidates"]["ivap (deployed)"]
    def ok(c):
        return {"logloss_1pct_better": c["log_loss"] <= 0.99 * base["log_loss"], "ece_le_0.02": c["ece"] <= 0.02,
                "distinct_ge_50": c["distinct_values"] >= 50,
                "cov90_each_class_ge_0.88": min(c["conformal"]["90"]["coverage_flood"], c["conformal"]["90"]["coverage_no_flood"]) >= 0.88}
    res["adoption"] = {n: ok(c) | {"adopt": all(ok(c).values())} for n, c in res["candidates"].items() if n != "ivap (deployed)"}
    winners = [n for n, a in res["adoption"].items() if a["adopt"]]
    res["decision"] = (f"candidate(s) passing the rule: {winners}; recorded for v1.0, to be re-checked on protocol P-2 before deployment"
                       if winners else "no candidate passes the pre-set rule; IVAP stays")
    (OUT / "rq4_calibration.json").write_text(json.dumps(res, indent=2), encoding="utf-8")

    rows = [{"calibrator": n, **{k: c[k] for k in ("log_loss", "brier", "ece", "distinct_values", "roc_auc")},
             "cov90_flood": c["conformal"]["90"]["coverage_flood"], "cov90_no_flood": c["conformal"]["90"]["coverage_no_flood"],
             "singleton_90": c["conformal"]["90"]["singleton_share"], "nested": c["conformal"]["nested"], "levels_distinct": c["conformal"]["levels_distinct"]}
            for n, c in res["candidates"].items()]
    md = ["# RQ4: calibration and conformal study (deployed XGBoost scores)", "",
          f"Calibrate on July 2023 ({res['calibration_rows']:,} hours, {res['calibration_positives']} flood hours); evaluate on 1–25 Aug 2023 "
          f"({res['test_rows']:,} hours, {res['test_positives']} flood hours). Rule fixed before the run: see `src/calibration_study.py`.", "",
          f"**Why the probabilities look quantised:** the model itself emits only {res['raw_distinct_scores_test']} distinct raw scores on the test month, "
          f"and {res['raw_top_score_share_test'] * 100:.0f} % of all test hours share the single most common score. Calibration can only re-map those levels; "
          "more resolution needs a finer model (WS-05.6: more trees with early stopping).", "",
          pd.DataFrame(rows).to_markdown(index=False), "", f"**Decision:** {res['decision']}.", ""]
    (OUT / "rq4_calibration.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    return res


if __name__ == "__main__":
    run()
