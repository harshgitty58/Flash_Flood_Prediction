"""
Objective 4B — SHAP explanations for the deployed XGBoost model.

Outputs (results/shap/):
  shap_global_importance.csv   mean |SHAP| per feature (log-odds units)
  shap_mean_by_district.csv    mean SHAP per feature per district
  shap_top_drivers.csv         top-3 signed drivers for every test + replay prediction
  shap_bar_chart.png           global bar chart
SHAP values explain the model's score, not physical causation.
Run: python -m src.explain
"""
import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import shap  # noqa: E402

from src.data_loader import FEATURE_EXPERIMENTS, FINAL_EXPERIMENT, load_ml_dataset  # noqa: E402
from src.model_config import RESULTS_DIR, XGB_MODEL_DIR  # noqa: E402

OUT_DIR = RESULTS_DIR / "shap"
TOP_K = 3


def run():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    feats = FEATURE_EXPERIMENTS[FINAL_EXPERIMENT]
    pipe = joblib.load(XGB_MODEL_DIR / "model.joblib")
    df = load_ml_dataset().drop_duplicates(["station", "datetime"])

    keys = pd.concat([pd.read_csv(RESULTS_DIR / "predictions" / f"{k}_xgboost.csv", parse_dates=["datetime"])
                      [["station", "datetime"]] for k in ("test", "replay")]).drop_duplicates()
    rows = df.merge(keys, on=["station", "datetime"]).reset_index(drop=True)
    X = pd.DataFrame(pipe[:-1].transform(rows[feats]), columns=feats)

    explainer = shap.TreeExplainer(pipe[-1])
    sv = explainer.shap_values(X)
    sv = pd.DataFrame(sv, columns=feats)

    glob = sv.abs().mean().sort_values(ascending=False).rename("mean_abs_shap").reset_index().rename(columns={"index": "feature"})
    glob.to_csv(OUT_DIR / "shap_global_importance.csv", index=False)
    sv.assign(district=rows["district"]).groupby("district").mean().round(5).to_csv(OUT_DIR / "shap_mean_by_district.csv")

    vals = sv.to_numpy()
    order = np.argsort(-np.abs(vals), axis=1)[:, :TOP_K]
    top = rows[["station", "datetime", "district"]].copy()
    for k in range(TOP_K):
        top[f"driver_{k + 1}"] = [feats[j] for j in order[:, k]]
        top[f"shap_{k + 1}"] = vals[np.arange(len(vals)), order[:, k]].round(4)
        top[f"value_{k + 1}"] = X.to_numpy()[np.arange(len(vals)), order[:, k]].round(3)
    top.to_csv(OUT_DIR / "shap_top_drivers.csv", index=False)

    g = glob.head(15).iloc[::-1]
    plt.figure(figsize=(7, 5))
    plt.barh(g["feature"], g["mean_abs_shap"], color="#2f8f5b")
    plt.xlabel("mean |SHAP| (log-odds)")
    plt.title("Global feature impact — deployed XGBoost")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "shap_bar_chart.png", dpi=150)
    print(glob.head(10).to_string(index=False))
    print(f"explained {len(rows):,} predictions, base value {float(np.ravel(explainer.expected_value)[0]):.3f}")


if __name__ == "__main__":
    run()
