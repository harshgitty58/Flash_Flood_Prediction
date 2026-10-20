"""
Objective 4A — Uncertainty quantification for the deployed XGBoost model.

1. Inductive Venn-Abers predictors (IVAP): for each score s, isotonic regression is fitted on the calibration
   scores plus (s, 0) and plus (s, 1), giving a probability interval [p0, p1] that is valid under exchangeability.
   Calibrated point estimate: p = p1 / (1 - p0 + p1).
2. Mondrian (class-conditional) conformal prediction on the calibrated scores. Non-conformity for class c is
   1 - p_c; p-values are computed within each class's calibration scores, so the rare FLOOD class gets its own
   guarantee. Outputs per prediction: prediction set at 90 %, confidence (1 - second-largest p-value) and
   credibility (largest p-value).

Calibration set = validation predictions of the deployed model (results/predictions/validation_xgboost.csv).
Run: python -m src.conformal
"""
import json

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

from src.model_config import RESULTS_DIR, TARGET_COL
from src.params import P

PRED_DIR = RESULTS_DIR / "predictions"
OUT_DIR = RESULTS_DIR / "conformal"
ALPHAS = tuple(P["conformal"]["alphas"])
GRID_POINTS = P["conformal"]["grid_points"]


def venn_abers(cal_s: np.ndarray, cal_y: np.ndarray, s: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (p0, p1) for each test score.

    Exact IVAP needs two isotonic fits per distinct score; with ~1M replay rows that is too slow, so p0/p1 are
    computed exactly on a grid of score quantiles (plus the extremes) and linearly interpolated in between.
    """
    grid = np.unique(np.concatenate([np.quantile(np.concatenate([cal_s, s]), np.linspace(0, 1, GRID_POINTS)),
                                     [s.min(), s.max()]]))
    g0, g1 = np.empty(len(grid)), np.empty(len(grid))
    xs = np.append(cal_s, 0.0)
    for i, u in enumerate(grid):
        xs[-1] = u
        for lab, out in ((0, g0), (1, g1)):
            ir = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip")
            ir.fit(xs, np.append(cal_y, lab))
            out[i] = ir.predict([u])[0]
    return np.interp(s, grid, g0), np.interp(s, grid, g1)


def mondrian_pvalues(cal_p: np.ndarray, cal_y: np.ndarray, p: np.ndarray) -> np.ndarray:
    """p-values for class 0 and class 1 (shape n x 2), class-conditional."""
    out = np.empty((len(p), 2))
    for c in (0, 1):
        cal_scores = np.sort(1 - np.where(cal_y == c, np.where(c == 1, cal_p, 1 - cal_p), np.nan))
        cal_scores = cal_scores[~np.isnan(cal_scores)]
        test_scores = 1 - (p if c == 1 else 1 - p)
        n_ge = len(cal_scores) - np.searchsorted(cal_scores, test_scores, side="left")
        out[:, c] = (n_ge + 1) / (len(cal_scores) + 1)
    return out


def calibrate(model: str = "xgboost") -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cal = pd.read_csv(PRED_DIR / f"validation_{model}.csv")
    cal_s, cal_y = cal["predicted_probability"].to_numpy(), cal[TARGET_COL].astype(int).to_numpy()

    # calibrated calibration-set probabilities (leave-in IVAP, used only to build conformal scores)
    c0, c1 = venn_abers(cal_s, cal_y, cal_s)
    cal_p = c1 / (1 - c0 + c1)

    def enrich(df: pd.DataFrame) -> pd.DataFrame:
        p0, p1 = venn_abers(cal_s, cal_y, df["predicted_probability"].to_numpy())
        df["va_lower"], df["va_upper"] = np.minimum(p0, p1), np.maximum(p0, p1)
        df["p_calibrated"] = p1 / (1 - p0 + p1)
        pv = mondrian_pvalues(cal_p, cal_y, df["p_calibrated"].to_numpy())
        top, second = pv.max(1), np.sort(pv, 1)[:, 0]
        df["cp_pvalue_no_flood"], df["cp_pvalue_flood"] = pv[:, 0], pv[:, 1]
        df["confidence"], df["credibility"] = 1 - second, top
        for a in ALPHAS:
            inc0, inc1 = pv[:, 0] > a, pv[:, 1] > a
            df[f"cp_set_{int((1 - a) * 100)}"] = np.select(
                [inc0 & inc1, inc1, inc0], ["UNCERTAIN", "FLOOD", "NO_FLOOD"], "EMPTY")
        return df

    test = enrich(pd.read_csv(PRED_DIR / f"test_{model}.csv"))
    test.to_csv(OUT_DIR / "cp_test_predictions.csv", index=False)
    replay = enrich(pd.read_csv(PRED_DIR / f"replay_{model}.csv"))
    replay.to_csv(OUT_DIR / "cp_replay_predictions.csv", index=False)
    pd.DataFrame({"score": cal_s, "y": cal_y, "p_calibrated": cal_p}).to_csv(OUT_DIR / "calibration_scores.csv", index=False)

    # coverage on the held-out test set (overall and per class)
    y = test[TARGET_COL].astype(int).to_numpy()
    rows = []
    for a in ALPHAS:
        col = test[f"cp_set_{int((1 - a) * 100)}"]
        covered = np.where(y == 1, col.isin(["FLOOD", "UNCERTAIN"]), col.isin(["NO_FLOOD", "UNCERTAIN"]))
        rows.append({"nominal": 1 - a,
                     "coverage_all": round(covered.mean(), 4),
                     "coverage_flood": round(covered[y == 1].mean(), 4) if (y == 1).any() else None,
                     "coverage_no_flood": round(covered[y == 0].mean(), 4),
                     "share_uncertain": round((col == "UNCERTAIN").mean(), 4),
                     "share_flood_singleton": round((col == "FLOOD").mean(), 4)})
    cov = pd.DataFrame(rows)
    cov.to_csv(OUT_DIR / "cp_coverage.csv", index=False)
    width = (test["va_upper"] - test["va_lower"])
    summary = {
        "calibration_rows": int(len(cal)), "calibration_positives": int(cal_y.sum()),
        "test_rows": int(len(test)), "test_positives": int(y.sum()),
        "mean_interval_width": round(float(width.mean()), 4),
        "brier_raw": round(float(np.mean((test["predicted_probability"] - y) ** 2)), 5),
        "brier_calibrated": round(float(np.mean((test["p_calibrated"] - y) ** 2)), 5),
        "coverage": rows,
    }
    (OUT_DIR / "cp_summary.json").write_text(json.dumps(summary, indent=2))
    md = ["# Conformal / Venn-Abers coverage report", "",
          f"Calibration: validation set ({summary['calibration_rows']} rows, {summary['calibration_positives']} positives). "
          f"Test: {summary['test_rows']} rows, {summary['test_positives']} positives.", "",
          cov.to_markdown(index=False), "",
          f"Mean Venn-Abers interval width on test: {summary['mean_interval_width']}. "
          f"Brier raw {summary['brier_raw']} → calibrated {summary['brier_calibrated']}.", "",
          "Caveat: with ~20 positives per split, class-1 coverage is estimated on very few points."]
    (OUT_DIR / "cp_coverage_report.md").write_text("\n".join(md), encoding="utf-8")
    print(cov.to_string(index=False)); print({k: v for k, v in summary.items() if k != "coverage"})
    return summary


if __name__ == "__main__":
    calibrate()
