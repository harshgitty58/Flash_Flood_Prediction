"""
Leave-one-event-out cross-validation (A3).

With only ~7 flood episodes in the labelled period, a single chronological split puts 1-2 events in the
test set, which is too fragile to compare models. Here each episode is held out in turn:
  test  = all labelled rows within +/- WINDOW_DAYS of the episode
  train = all labelled rows further than BUFFER_DAYS from it (past and future)
Out-of-fold predictions are pooled to compute metrics per feature set.
Run: python -m src.event_cv
"""
import json

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score
from xgboost import XGBClassifier

from src.data_loader import FEATURE_EXPERIMENTS, load_ml_dataset
from src.model_config import RANDOM_STATE, RESULTS_DIR, TARGET_COL
from src.params import P

WINDOW_DAYS, BUFFER_DAYS, MERGE_DAYS = (P["event_cv"][k] for k in ("window_days", "buffer_days", "merge_days"))
OUT_DIR = RESULTS_DIR / "event_cv"


def episodes(df: pd.DataFrame) -> list[pd.Timestamp]:
    """Positive dates merged into episodes when they are within MERGE_DAYS of each other."""
    days = sorted(df.loc[df[TARGET_COL] == 1, "datetime"].dt.normalize().unique())
    eps: list[list[pd.Timestamp]] = []
    for d in days:
        if eps and (d - eps[-1][-1]).days <= MERGE_DAYS:
            eps[-1].append(d)
        else:
            eps.append([d])
    return [pd.Timestamp(e[0]) + (pd.Timestamp(e[-1]) - pd.Timestamp(e[0])) / 2 for e in eps]


def run():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_ml_dataset()
    df = df[df[TARGET_COL].notna()].reset_index(drop=True)
    df[TARGET_COL] = df[TARGET_COL].astype(int)
    params = json.loads((RESULTS_DIR / "hyperparameter_tuning" / "xgboost_best_params.json").read_text())
    params = {k.replace("classifier__", ""): v for k, v in params.items()}

    eps = episodes(df)
    print(f"{len(eps)} flood episodes:", [e.date().isoformat() for e in eps])
    rows, oof = [], []
    for exp, feats in FEATURE_EXPERIMENTS.items():
        preds = []
        for k, c in enumerate(eps):
            gap = (df["datetime"] - c).abs()
            test = df[gap <= pd.Timedelta(days=WINDOW_DAYS)]
            train = df[gap > pd.Timedelta(days=BUFFER_DAYS)]
            if train[TARGET_COL].sum() == 0 or test[TARGET_COL].nunique() < 2:
                continue
            spw = (train[TARGET_COL] == 0).sum() / max(1, train[TARGET_COL].sum())
            m = XGBClassifier(**{**params, "scale_pos_weight": spw}, random_state=RANDOM_STATE, eval_metric="logloss", n_jobs=-1)
            m.fit(train[feats], train[TARGET_COL])
            p = test[["station", "datetime", "district", TARGET_COL]].copy()
            p["p"], p["fold"], p["experiment"] = m.predict_proba(test[feats])[:, 1], k, exp
            preds.append(p)
        P = pd.concat(preds)
        oof.append(P)
        fold_auc = [roc_auc_score(g[TARGET_COL], g["p"]) for _, g in P.groupby("fold")]
        rows.append({
            "experiment": exp, "features": len(feats), "folds": P["fold"].nunique(),
            "rows": len(P), "positives": int(P[TARGET_COL].sum()),
            "pooled_roc_auc": round(roc_auc_score(P[TARGET_COL], P["p"]), 4),
            "pooled_pr_auc": round(average_precision_score(P[TARGET_COL], P["p"]), 4),
            "base_rate": round(P[TARGET_COL].mean(), 4),
            "mean_fold_roc_auc": round(float(np.mean(fold_auc)), 4),
            "min_fold_roc_auc": round(float(np.min(fold_auc)), 4),
        })
        print(rows[-1])
    res = pd.DataFrame(rows)
    res.to_csv(OUT_DIR / "event_cv_summary.csv", index=False)
    pd.concat(oof).to_csv(OUT_DIR / "event_cv_oof_predictions.csv", index=False)
    return res




def lead_times(experiment: str | None = None, far: float = 0.05) -> pd.DataFrame:
    """Event-level detection from out-of-fold predictions.

    Alarm threshold = (1 - far) quantile of OOF scores on non-flood rows (i.e. ~5 % false-alarm rate per hour).
    For each recorded flood (district, start date) a hit means some station in that district crossed the
    threshold in the 48 h before the event start; lead time = event start - first crossing.
    """
    from src.data_loader import FINAL_EXPERIMENT
    from src.config import CLEANED_DIR
    experiment = experiment or FINAL_EXPERIMENT
    oof = pd.read_csv(OUT_DIR / "event_cv_oof_predictions.csv", parse_dates=["datetime"])
    oof = oof[oof["experiment"] == experiment]
    thr = oof.loc[oof[TARGET_COL] == 0, "p"].quantile(1 - far)
    inv = pd.read_parquet(CLEANED_DIR / "flood_inventory_cleaned.parquet")
    inv = inv[(inv["start_datetime"] >= oof["datetime"].min()) & (inv["start_datetime"] <= oof["datetime"].max() + pd.Timedelta(days=1))]
    rows = []
    for _, e in inv.drop_duplicates(["district", "start_datetime"]).iterrows():
        w = oof[(oof["district"] == e["district"]) & (oof["datetime"] < e["start_datetime"] + pd.Timedelta(hours=24))
                & (oof["datetime"] >= e["start_datetime"] - pd.Timedelta(hours=48))]
        if w.empty:
            continue  # no reporting station in that district around the event
        hit = w[w["p"] >= thr]
        lead = (e["start_datetime"] - hit["datetime"].min()).total_seconds() / 3600 if len(hit) else None
        rows.append({"district": e["district"], "event_start": e["start_datetime"].date(), "stations": w["station"].nunique(),
                     "max_p": round(w["p"].max(), 3), "detected": bool(len(hit)), "lead_time_h": lead})
    res = pd.DataFrame(rows)
    res.to_csv(OUT_DIR / "event_lead_times.csv", index=False)
    summary = {"experiment": experiment, "alarm_threshold": round(float(thr), 4), "hourly_false_alarm_rate": far,
               "events_evaluated": int(len(res)), "events_detected": int(res["detected"].sum()) if len(res) else 0,
               "median_lead_time_h": float(res["lead_time_h"].median()) if res["detected"].any() else None}
    (OUT_DIR / "event_lead_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(res.to_string(index=False)); print(summary)
    return res


if __name__ == "__main__":
    run()
    lead_times()
