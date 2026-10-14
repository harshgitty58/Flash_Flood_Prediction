"""
Objective 4C — Robustness of the deployed model to degraded observations (inference-time, no retraining).

Evaluated on all labelled rows the model was not trained on (validation + test). Missing inputs are set to NaN,
which the pipeline's training-median imputer fills — exactly what happens when a sensor drops out live.
Run: python -m src.robustness
"""
import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import average_precision_score, roc_auc_score  # noqa: E402

from src.data_loader import (DISCHARGE_FEATURES, FEATURE_EXPERIMENTS, FINAL_EXPERIMENT,  # noqa: E402
                             HISTORICAL_FLOOD_FEATURES, LANDSLIDE_FEATURES, RAINFALL_FEATURES, load_ml_dataset)
from src.model_config import RANDOM_STATE, RESULTS_DIR, TARGET_COL, XGB_MODEL_DIR  # noqa: E402

OUT_DIR = RESULTS_DIR / "robustness"


def run():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(RANDOM_STATE)
    feats = FEATURE_EXPERIMENTS[FINAL_EXPERIMENT]
    pipe = joblib.load(XGB_MODEL_DIR / "model.joblib")
    df = load_ml_dataset().drop_duplicates(["station", "datetime"])
    keys = pd.concat([pd.read_csv(RESULTS_DIR / "predictions" / f"{k}_xgboost.csv", parse_dates=["datetime"])[["station", "datetime"]]
                      for k in ("validation", "test")])
    ev = df.merge(keys, on=["station", "datetime"])
    X0, y = ev[feats].copy(), ev[TARGET_COL].astype(int).to_numpy()
    rain = [f for f in RAINFALL_FEATURES if f in feats]
    sd = X0[rain].std()

    def drop(cols):
        def f(X):
            X = X.copy(); X[[c for c in cols if c in X]] = np.nan; return X
        return f

    def noise(frac):
        def f(X):
            X = X.copy(); X[rain] = (X[rain] + rng.normal(0, 1, X[rain].shape) * (sd * frac).to_numpy()).clip(lower=0); return X
        return f

    def dropout(frac):
        def f(X):
            X = X.copy(); X = X.mask(rng.random(X.shape) < frac); return X
        return f

    scenarios = [("Baseline (all inputs)", "baseline", lambda X: X)]
    scenarios += [(f"R1 rainfall noise sd={int(f * 100)}% of std", "noise", noise(f)) for f in (0.05, 0.1, 0.2, 0.5)]
    scenarios += [("R3 river discharge offline", "outage", drop(DISCHARGE_FEATURES)),
                  ("R3b rainfall gauge offline", "outage", drop(RAINFALL_FEATURES)),
                  ("R3c flood-history records unavailable", "outage", drop(HISTORICAL_FLOOD_FEATURES)),
                  ("R3d landslide inventory unavailable", "outage", drop(LANDSLIDE_FEATURES))]
    scenarios += [(f"R4 random dropout {int(f * 100)}% of inputs", "dropout", dropout(f)) for f in (0.1, 0.25, 0.5)]
    scenarios += [("R5 noisy rain (20%) + discharge offline", "combined", lambda X: drop(DISCHARGE_FEATURES)(noise(0.2)(X)))]

    base_p = None
    rows = []
    for name, kind, fn in scenarios:
        p = pipe.predict_proba(fn(X0))[:, 1]
        base_p = p if base_p is None else base_p
        rows.append({"scenario": name, "kind": kind, "roc_auc": round(roc_auc_score(y, p), 4),
                     "pr_auc": round(average_precision_score(y, p), 4),
                     "mean_abs_score_change": round(float(np.abs(p - base_p).mean()), 4),
                     "flood_rows_mean_score": round(float(p[y == 1].mean()), 4)})
    res = pd.DataFrame(rows)
    b = res.iloc[0]
    res["roc_auc_drop"] = (b["roc_auc"] - res["roc_auc"]).round(4)
    res.to_csv(OUT_DIR / "robustness_summary.csv", index=False)

    worst = res.iloc[1:].sort_values("roc_auc").iloc[0]
    md = ["# Robustness report (inference-time degradation)", "",
          f"Evaluated on {len(ev):,} labelled held-out rows ({int(y.sum())} floods). Missing inputs → training-median imputation.", "",
          res.to_markdown(index=False), "",
          f"Most damaging scenario: **{worst['scenario']}** (ROC-AUC {b['roc_auc']} → {worst['roc_auc']})."]
    (OUT_DIR / "robustness_report.md").write_text("\n".join(md), encoding="utf-8")

    plt.figure(figsize=(8, 4.5))
    r = res.iloc[::-1]
    plt.barh(r["scenario"], r["roc_auc"], color=["#2f8f5b" if k == "baseline" else "#4fb3f0" for k in r["kind"]])
    plt.axvline(0.5, color="grey", ls="--", lw=1)
    plt.xlabel("ROC-AUC"); plt.title("Robustness to degraded inputs — deployed XGBoost"); plt.tight_layout()
    plt.savefig(OUT_DIR / "robustness_curves.png", dpi=150)
    print(res.to_string(index=False))


if __name__ == "__main__":
    run()
