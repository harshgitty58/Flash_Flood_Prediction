"""
Label experiment (LABELS_PLAN.md §0 L1/L3, §5) — does better ground truth improve the model, or only the score?

Variants (same rows, features, splits, tuned hyperparameters and threshold rule; only labels differ):
  v1         IMD inventory (after the L0 district-name fix)
  v2         IMD ∪ SANDRP ∪ situation reports (confidence >= medium), clipped to IMD's coverage end
  v2_masked  v2 + uncertain negatives removed: label-0 district-days inside EM-DAT state-wide flood windows with
             district max rain_24h >= 64.5 mm (IMD 'heavy'), dropped from training and scoring

Every model is scored against every truth (2×2 grid), so a gain that only comes from relabelling the test set is
visible: a v2-trained model must also do at least as well as v1 on v1's own truth to count as a real improvement.
Hyperparameters are the ones tuned on v1 — a conservative choice for v2.
Outputs: results/labels/label_experiment.json, label_experiment_grid.csv
Run: python -m src.label_experiment
"""
import json

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from src.config import CLEANED_DIR, PROJECT_ROOT
from src.data_loader import FEATURE_EXPERIMENTS, FINAL_EXPERIMENT, load_ml_dataset
from src.data_window import STUDY_START
from src.evaluate import compute_all_metrics, find_optimal_threshold
from src.event_cv import BUFFER_DAYS, MERGE_DAYS, WINDOW_DAYS
from src.model_config import RANDOM_STATE, RESULTS_DIR, TARGET_COL, TRAIN_END_DATE, TUNING_DIR, VAL_END_DATE
from src.preprocessing import get_logistic_preprocessor, get_tree_preprocessor
from src.target import construct_flood_target_24h, v2_inventory
from src.verification import boot_ci, contingency, scores

OUT = RESULTS_DIR / "labels"
HEAVY_24H = 64.5
MODELS = {"XGBoost": ("xgboost", lambda: XGBClassifier(random_state=RANDOM_STATE, eval_metric="logloss", n_jobs=-1), get_tree_preprocessor),
          "Random Forest": ("random_forest", lambda: RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=-1), get_tree_preprocessor),
          "Logistic Regression": ("logistic_regression", lambda: LogisticRegression(random_state=RANDOM_STATE, max_iter=1000), get_logistic_preprocessor)}


def build_labels(df: pd.DataFrame) -> pd.DataFrame:
    inv = pd.read_parquet(CLEANED_DIR / "flood_inventory_cleaned.parquet")
    end = inv["start_datetime"].max()
    base = df[["station", "district", "datetime"]].copy()
    df["y_v1"] = df[TARGET_COL]
    df["y_v2"] = construct_flood_target_24h(base.copy(), v2_inventory(end), coverage_end=end)["flood_event_24h"].to_numpy()

    # L3 mask: label-0 district-days inside state-wide EM-DAT flood windows with heavy district rain
    ctx = pd.read_csv(PROJECT_ROOT / "data/external/labels/emdat_uttarakhand_context.csv", parse_dates=["start", "end"])
    day = df["datetime"].dt.normalize()
    in_ctx = np.zeros(len(df), bool)
    for _, c in ctx.iterrows():
        in_ctx |= ((day >= c["start"]) & (day <= c["end"])).to_numpy()
    dmax = df.groupby(["district", day])["rain_24h"].transform("max").to_numpy()
    dlab = df.assign(_d=day).groupby(["district", "_d"])["y_v2"].transform("max").to_numpy()
    mask = in_ctx & (dmax >= HEAVY_24H) & (dlab == 0)
    df["y_v2_masked"] = np.where(mask, np.nan, df["y_v2"])
    return df


def model(name: str, y_train: pd.Series) -> Pipeline:
    key, make, prep = MODELS[name]
    params = json.loads((TUNING_DIR / f"{key}_best_params.json").read_text())
    pipe = Pipeline([("preprocessor", prep()), ("classifier", make())]).set_params(**params)
    if name == "XGBoost":
        pipe.set_params(classifier__scale_pos_weight=float((y_train == 0).sum() / max(1, (y_train == 1).sum())))
    return pipe


def district_day(t: pd.DataFrame, p: np.ndarray, thr: float, y: str) -> dict:
    d = t.assign(warn=(p >= thr), day=t["datetime"].dt.normalize())
    d = d[d[y].notna()].groupby(["district", "day"]).agg(warn=("warn", "max"), obs=(y, "max")).reset_index()
    f = lambda g: scores(contingency(g["warn"].to_numpy(), g["obs"].to_numpy()))  # noqa: E731
    pt = {k: (round(v, 3) if v == v else None) for k, v in f(d).items()}
    return {**contingency(d["warn"].to_numpy(), d["obs"].to_numpy()), **pt, "ci95": boot_ci(d, "day", f, n=300)}


def event_cv(df: pd.DataFrame, y: str, feats: list) -> dict:
    """Leave-one-episode-out with the same WINDOW/BUFFER/MERGE rules as src.event_cv, episodes from this truth."""
    d = df[df[y].notna()].reset_index(drop=True)
    days = sorted(d.loc[d[y] == 1, "datetime"].dt.normalize().unique())
    eps = []
    for x in days:
        if eps and (x - eps[-1][-1]).days <= MERGE_DAYS:
            eps[-1].append(x)
        else:
            eps.append([x])
    centres = [pd.Timestamp(e[0]) + (pd.Timestamp(e[-1]) - pd.Timestamp(e[0])) / 2 for e in eps]
    preds = []
    for c in centres:
        gap = (d["datetime"] - c).abs()
        te, tr = d[gap <= pd.Timedelta(days=WINDOW_DAYS)], d[gap > pd.Timedelta(days=BUFFER_DAYS)]
        if tr[y].sum() == 0 or te[y].nunique() < 2:
            continue
        m = model("XGBoost", tr[y]).fit(tr[feats], tr[y].astype(int))
        preds.append(pd.DataFrame({"y": te[y].to_numpy(), "p": m.predict_proba(te[feats])[:, 1]}))
    P = pd.concat(preds)
    return {"episodes": len(centres), "folds": len(preds), "pooled_roc_auc": round(roc_auc_score(P["y"], P["p"]), 4),
            "pooled_pr_auc": round(average_precision_score(P["y"], P["p"]), 4), "base_rate": round(P["y"].mean(), 4)}


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    feats = FEATURE_EXPERIMENTS[FINAL_EXPERIMENT]
    df = load_ml_dataset()
    df = df[df[TARGET_COL].notna() & (df["datetime"] >= STUDY_START)].reset_index(drop=True)
    df = build_labels(df)
    tr_m = df["datetime"] < pd.Timestamp(TRAIN_END_DATE)
    va_m = (df["datetime"] >= pd.Timestamp(TRAIN_END_DATE)) & (df["datetime"] < pd.Timestamp(VAL_END_DATE))
    te = df[df["datetime"] >= pd.Timestamp(VAL_END_DATE)]
    variants = ["y_v1", "y_v2", "y_v2_masked"]

    label_stats = {v: {s: {"rows": int(df.loc[m, v].notna().sum()), "positives": int(df.loc[m, v].sum()),
                           "district_days_pos": int(df.loc[m & (df[v] == 1)].assign(d=df["datetime"].dt.normalize()).drop_duplicates(["district", "d"]).shape[0])}
                       for s, m in (("train", tr_m), ("validation", va_m), ("test", df["datetime"] >= pd.Timestamp(VAL_END_DATE)))}
                   for v in variants}
    print(json.dumps(label_stats, indent=1))

    grid = []
    for name in MODELS:
        for v in variants:
            tr, va = df[tr_m & df[v].notna()], df[va_m & df[v].notna()]
            m = model(name, tr[v]).fit(tr[feats], tr[v].astype(int))
            thr, _ = find_optimal_threshold(va[v].astype(int).to_numpy(), m.predict_proba(va[feats])[:, 1])
            p_te = m.predict_proba(te[feats])[:, 1]
            for truth in variants:
                ok = te[truth].notna().to_numpy()
                yt = te[truth].to_numpy()[ok].astype(int)
                sh = compute_all_metrics(yt, p_te[ok], threshold=thr)
                dd = district_day(te, p_te, thr, truth)
                grid.append({"model": name, "trained_on": v[2:], "scored_on": truth[2:], "threshold": thr,
                             "roc_auc": round(sh["roc_auc"], 4), "pr_auc": round(sh["pr_auc"], 4), "precision": round(sh["precision"], 4),
                             "recall": round(sh["recall"], 4), "f1": round(sh["f1"], 4), "test_base_rate": round(yt.mean(), 4),
                             "dd_POD": dd["POD"], "dd_FAR": dd["FAR"], "dd_CSI": dd["CSI"], "dd_HSS": dd["HSS"],
                             "dd_CSI_ci95": dd["ci95"]["CSI"], "dd_tp_fp_fn": f"{dd['tp']}/{dd['fp']}/{dd['fn']}"})
                print({k: grid[-1][k] for k in ("model", "trained_on", "scored_on", "pr_auc", "f1", "dd_POD", "dd_FAR", "dd_CSI")})
    G = pd.DataFrame(grid)
    G.to_csv(OUT / "label_experiment_grid.csv", index=False)

    ecv = {v[2:]: event_cv(df, v, feats) for v in variants}
    print(json.dumps(ecv, indent=1))

    x = G[G["model"] == "XGBoost"].set_index(["trained_on", "scored_on"])
    better = lambda a, b, s, k: (x.loc[(a, s), k] or 0) >= (x.loc[(b, s), k] or 0)  # noqa: E731
    decision = {
        "rule": "adopt v2 if, for XGBoost, the v2-trained model is at least as good as v1-trained on BOTH truths "
                "(PR-AUC and district-day CSI) and event-CV PR-AUC improves",
        "v2_on_v1_truth_ok": bool(better("v2", "v1", "v1", "pr_auc") and better("v2", "v1", "v1", "dd_CSI")),
        "v2_on_v2_truth_ok": bool(better("v2", "v1", "v2", "pr_auc") and better("v2", "v1", "v2", "dd_CSI")),
        "event_cv_ok": ecv["v2"]["pooled_pr_auc"] > ecv["v1"]["pooled_pr_auc"],
    }
    decision["adopt_v2"] = all(decision[k] for k in ("v2_on_v1_truth_ok", "v2_on_v2_truth_ok", "event_cv_ok"))
    (OUT / "label_experiment.json").write_text(json.dumps({"labels": label_stats, "event_cv": ecv, "decision": decision,
                                                             "grid": G.to_dict("records")}, indent=2, default=str))
    print(json.dumps(decision, indent=1))
    return G


if __name__ == "__main__":
    run()
