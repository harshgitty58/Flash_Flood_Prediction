"""
E3 (MODEL_UPGRADE_PLAN.md) — pooled district-day model + "top-3 districts today" ranking.

Data: results/district_day/dataset.parquet (CWC + USDMA hydromet + ERA5, every district every day; src.district_day).
Model: logistic regression with the district_day features plus one-hot district intercepts; the L2 penalty (C=0.1)
shrinks each district's intercept towards the shared mean (≈ random intercepts with a Gaussian prior), rain slopes shared.
Threshold (fixed before the run, no validation tuning): the training-period cut-off where alert district-days =
2 × observed flood district-days (frequency bias 2).
Ranking: each day, districts are ranked by probability; recall@3 = share of flood district-days (test month) /
documented events (Sep 2023 → 2025, any day in [date-1, end]) whose district was in that day's top 3.
Baseline ranking: district prior = training flood rate (ties broken by DFSI).

Adoption as the alert layer: same three-part rule as src.district_day (test CSI vs hybrid on common district-days,
external POD, monsoon-2024 alert district-days). Ranking view offered if recall@3 beats the prior on BOTH the test
month and the external events.
Output: results/model_upgrade/e3_district_pooled.json
Run: python -m src.district_pooled   (after src.district_day)
"""
import json

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline

from src.config import PROJECT_ROOT
from src.district_day import FEATURES, cat, external
from src.model_config import RESULTS_DIR, TRAIN_END_DATE, VAL_END_DATE
from src.preprocessing import get_logistic_preprocessor

OUT = RESULTS_DIR / "model_upgrade"


def recall_at_k(d: pd.DataFrame, score: str, targets: list[tuple], k=3) -> float:
    top = set()
    for day, g in d.groupby("day"):
        top.update((x, day) for x in g.nlargest(k, score)["district"])
    hits = [any((x, t) in top for t in days) for x, days in targets]
    return round(float(np.mean(hits)), 3) if hits else None


def run():
    d = pd.read_parquet(RESULTS_DIR / "district_day/dataset.parquet")
    X = pd.concat([d[FEATURES], pd.get_dummies(d["district"], prefix="d", dtype=float)], axis=1)
    cols = list(X.columns)
    tr_m = (d["day"] < pd.Timestamp(TRAIN_END_DATE)) & d["y"].notna()
    m = Pipeline([("pre", get_logistic_preprocessor()), ("clf", LogisticRegression(C=0.1, class_weight="balanced", max_iter=3000))])
    m.fit(X.loc[tr_m, cols], d.loc[tr_m, "y"].astype(int))
    d["p"] = m.predict_proba(X[cols])[:, 1]
    p_tr = np.sort(d.loc[tr_m, "p"].to_numpy())[::-1]
    thr = float(p_tr[min(len(p_tr) - 1, 2 * int(d.loc[tr_m, "y"].sum()))])
    d["alert"] = (d["p"] >= thr).astype(int)
    prior = d[tr_m].groupby("district")["y"].mean() + d.groupby("district")["district_flood_severity_index"].first() * 1e-6
    d["prior"] = d["district"].map(prior)

    pred = pd.read_csv(RESULTS_DIR / "district_day/predictions.csv", parse_dates=["day"])[["district", "day", "hybrid_alert"]]
    d = d.merge(pred, on=["district", "day"], how="left")
    te = d[(d["day"] >= pd.Timestamp(VAL_END_DATE)) & d["y"].notna()]
    common = te[te["hybrid_alert"].notna()]

    ev = pd.read_csv(PROJECT_ROOT / "data/external/labels/labels_2022_2025.csv", parse_dates=["date", "end_date"])
    ev = ev[ev["date"] > pd.Timestamp("2023-08-26")]
    ext_targets = [(e["district"], list(pd.date_range(e["date"] - pd.Timedelta(days=1), e["end_date"]))) for _, e in ev.iterrows()]
    te_targets = [(x, [t]) for x, t in te.loc[te["y"] == 1, ["district", "day"]].itertuples(index=False)]
    ext_days = d[d["day"] > pd.Timestamp("2023-08-26")]

    res = {"threshold_rule": "frequency bias 2 on training", "threshold": round(thr, 4),
           "test": {"roc_auc": round(roc_auc_score(te["y"], te["p"]), 3), "pr_auc": round(average_precision_score(te["y"], te["p"]), 3),
                    "base_rate": round(te["y"].mean(), 3), **cat(te["alert"].to_numpy(), te["y"].to_numpy())},
           "test_common": {"pooled": cat(common["alert"].to_numpy(), common["y"].to_numpy(), common["day"]),
                           "hybrid": cat(common["hybrid_alert"].to_numpy().astype(bool), common["y"].to_numpy(), common["day"])},
           "external_pooled": external(d, "alert"), "external_hybrid": external(d, "hybrid_alert"),
           "ranking_recall_at_3": {"test_model": recall_at_k(te, "p", te_targets), "test_prior": recall_at_k(te, "prior", te_targets),
                                   "external_model": recall_at_k(ext_days, "p", ext_targets), "external_prior": recall_at_k(ext_days, "prior", ext_targets),
                                   "chance": round(3 / 13, 3)}}
    a, b = res["test_common"]["pooled"], res["test_common"]["hybrid"]
    xa, xb = res["external_pooled"], res["external_hybrid"]
    burden = lambda x: next((r["alert_district_days"] for r in x["alert_burden"] if r["monsoon"] == 2024), 0)  # noqa: E731
    r = res["ranking_recall_at_3"]
    res["decision"] = {"csi_ok": (a["CSI"] or 0) >= (b["CSI"] or 0), "external_pod_ok": (xa["POD"] or 0) >= (xb["POD"] or 0),
                       "burden_ok": burden(xa) <= burden(xb)}
    res["decision"]["adopt_alert_layer"] = all(res["decision"].values())
    res["decision"]["offer_ranking_view"] = (r["test_model"] or 0) > (r["test_prior"] or 0) and (r["external_model"] or 0) > (r["external_prior"] or 0)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "e3_district_pooled.json").write_text(json.dumps(res, indent=2, default=str))
    d.loc[d["day"] > pd.Timestamp(VAL_END_DATE), ["district", "day", "p", "prior"]].to_csv(OUT / "e3_district_scores.csv", index=False)
    print(json.dumps({k: res[k] for k in ("threshold", "test", "ranking_recall_at_3", "decision")}, indent=1, default=str))
    print("test common:", {k: {m: v[m] for m in ("POD", "FAR", "CSI")} for k, v in res["test_common"].items()},
          "| external:", {k: (res[k]["detected"], res[k]["events_scored"], [x["alert_district_days"] for x in res[k]["alert_burden"]]) for k in ("external_pooled", "external_hybrid")})
    return res


if __name__ == "__main__":
    run()
