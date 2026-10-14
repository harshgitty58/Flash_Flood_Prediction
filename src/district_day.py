"""
L5 + L7 — district-day flood model with multi-source rainfall (LABELS_PLAN.md §0).

Why: labels are district-days, but the deployed model scores station-hours, so one district flood becomes hundreds
of station-hour hits/misses, and a district with its CWC gauges offline gets no warning at all (8 of 29 external
events). Here every district gets one prediction per day from all rain sources that are available by the end of
that day:
  CWC gauges      district max / mean of station daily totals, max hourly intensity, gauges reporting
  USDMA hydromet  08:30 + 17:30 reports of day D (≈ D-1 17:30 → D 17:30), district max / mean, stations reporting
  ERA5            reanalysis daily totals at every gauge site (never offline), district max / mean, soil moisture
  + 3-day totals of each source, static district susceptibility, month.
Target (same as the hourly model): flood recorded in the district on D or D+1 (IMD v1, after the L0 fix).
Splits: same dates as the hourly model (train < 2023-07-01, validation Jul 2023, test 1-25 Aug 2023).
Models: L2 logistic regression (C=0.1, balanced) and a shallow monotone XGBoost (rain ↑ ⇒ risk ↑); the one with
the better validation PR-AUC is kept, its alert threshold maximises validation district-day CSI.

Adoption rule (fixed before the run): the district-day layer is adopted as the deployed district outlook only if
  (1) test district-day CSI ≥ the current hybrid tier's CSI on the same district-days, AND
  (2) external-validation POD (all events after Aug 2023) ≥ the hybrid's, AND
  (3) monsoon-2024 ALERT district-days ≤ the hybrid's.
Outputs: results/district_day/{dataset.parquet, predictions.csv, summary.json}
Run: python -m src.district_day
"""
import json

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from src.config import CLEANED_DIR, OFFICIAL_UTTARAKHAND_DISTRICTS, PROJECT_ROOT
from src.data_loader import load_ml_dataset
from src.data_window import STUDY_START
from src.model_config import RANDOM_STATE, RESULTS_DIR, TRAIN_END_DATE, VAL_END_DATE
from src.preprocessing import get_logistic_preprocessor, get_tree_preprocessor
from src.verification import boot_ci, contingency, scores

OUT = RESULTS_DIR / "district_day"
HM_DISTRICT = {"Tehri": "Tehri Garhwal", "Pauri": "Pauri Garhwal", "US Nagar": "Udham Singh Nagar"}
RAIN = ["rain_cwc_max", "rain_cwc_mean", "rain_cwc_imax", "rain_hm_max", "rain_hm_mean", "era5_max", "era5_mean",
        "rain_cwc_max_3d", "rain_hm_max_3d", "era5_max_3d", "rain_any_max"]
STATIC = ["district_flood_severity_index", "district_flooded_area_pct", "district_historical_fatalities",
          "district_mean_flood_duration_days", "landslide_count_10km", "is_landslide_hotspot"]
FEATURES = RAIN + ["sm_0_7", "n_cwc", "n_hm"] + STATIC + ["is_monsoon"]
RANK = {"NORMAL": 0, "WATCH": 1, "ALERT": 2, "SEVERE": 3, "EXTREME": 4}


# ------------------------------------------------------------------ dataset
def build() -> pd.DataFrame:
    ds = load_ml_dataset()
    ds["day"] = ds["datetime"].dt.normalize()
    st = ds.groupby(["station", "day"]).agg(district=("district", "first"), tot=("rain_1h", "sum"), imax=("rain_1h", "max"), n=("rain_1h", "count"))
    st = st[st["n"] >= 12].reset_index()  # a gauge counts for the day only with >= 12 reporting hours
    cwc = st.groupby(["district", "day"]).agg(rain_cwc_max=("tot", "max"), rain_cwc_mean=("tot", "mean"), rain_cwc_imax=("imax", "max"), n_cwc=("station", "nunique"))

    smap = ds.groupby("station")["district"].first()
    e = []
    for f in sorted((PROJECT_ROOT / "data/external/era5").glob("*.csv")):
        if f.stem in smap:
            x = pd.read_csv(f, usecols=["datetime", "era5_precip", "sm_0_7"], parse_dates=["datetime"])
            x["day"] = x["datetime"].dt.normalize()
            e.append(x.groupby("day").agg(tot=("era5_precip", "sum"), sm=("sm_0_7", "mean")).assign(district=smap[f.stem]).reset_index())
    e = pd.concat(e)
    era = e.groupby(["district", "day"]).agg(era5_max=("tot", "max"), era5_mean=("tot", "mean"), sm_0_7=("sm", "mean"))

    h = pd.read_csv(PROJECT_ROOT / "data/external/hydromet/hydromet_observations.csv", parse_dates=["datetime"])
    h["district"] = h["district"].replace(HM_DISTRICT)
    h["day"] = h["datetime"].dt.normalize()  # 08:30 + 17:30 of day D: both known by the end of D
    hs = h.groupby(["station", "day"]).agg(district=("district", "first"), tot=("rain_mm", "sum")).reset_index()
    hm = hs.groupby(["district", "day"]).agg(rain_hm_max=("tot", "max"), rain_hm_mean=("tot", "mean"), n_hm=("station", "nunique"))

    days = pd.date_range(STUDY_START, ds["day"].max())
    grid = pd.MultiIndex.from_product([OFFICIAL_UTTARAKHAND_DISTRICTS, days], names=["district", "day"])
    d = pd.DataFrame(index=grid).join(cwc).join(era).join(hm).reset_index().sort_values(["district", "day"])
    d[["n_cwc", "n_hm"]] = d[["n_cwc", "n_hm"]].fillna(0)
    for c in ("rain_cwc_max", "rain_hm_max", "era5_max"):
        d[f"{c}_3d"] = d.groupby("district")[c].transform(lambda s: s.rolling(3, min_periods=1).sum())
    d["rain_any_max"] = d[["rain_cwc_max", "rain_hm_max"]].max(axis=1)
    static = ds.groupby("district")[STATIC].mean()
    d = d.merge(static, left_on="district", right_index=True, how="left")
    d["is_monsoon"] = d["day"].dt.month.between(6, 9).astype(int)

    inv = pd.read_parquet(CLEANED_DIR / "flood_inventory_cleaned.parquet")
    inv = inv[inv["district"].isin(OFFICIAL_UTTARAKHAND_DISTRICTS)]
    ev = set(zip(inv["district"], inv["start_datetime"].dt.normalize()))
    end = inv["start_datetime"].max().normalize()
    d["y"] = [float((x, t) in ev or (x, t + pd.Timedelta(days=1)) in ev) for x, t in zip(d["district"], d["day"])]
    d.loc[d["day"] + pd.Timedelta(days=1) > end, "y"] = np.nan
    lab = pd.read_csv(PROJECT_ROOT / "data/external/labels/labels_daily.csv", parse_dates=["date"])
    lab = lab[(lab["date_confidence"] != "low") & (lab["date"] <= end)]
    ev2 = set(zip(lab["district"], lab["date"]))
    d["y_v2"] = [float((x, t) in ev2 or (x, t + pd.Timedelta(days=1)) in ev2) for x, t in zip(d["district"], d["day"])]
    d.loc[d["y"].isna(), "y_v2"] = np.nan
    return d.reset_index(drop=True)


# ------------------------------------------------------------------ models
def models(y: pd.Series) -> dict:
    mono = tuple(1 if f in RAIN else 0 for f in FEATURES)
    spw = float((y == 0).sum() / max(1, (y == 1).sum()))
    return {
        "logistic": Pipeline([("pre", get_logistic_preprocessor()), ("clf", LogisticRegression(C=0.1, class_weight="balanced", max_iter=2000))]),
        "xgb_monotone": Pipeline([("pre", get_tree_preprocessor()), ("clf", XGBClassifier(n_estimators=200, max_depth=2, learning_rate=0.05, subsample=0.8,
                                  colsample_bytree=0.8, min_child_weight=2, monotone_constraints=mono, scale_pos_weight=spw,
                                  random_state=RANDOM_STATE, eval_metric="logloss", n_jobs=-1))]),
    }


def cat(warn: np.ndarray, obs: np.ndarray, days: pd.Series | None = None) -> dict:
    c = contingency(warn, obs)
    out = {**c, **{k: (round(v, 3) if v == v else None) for k, v in scores(c).items()}}
    if days is not None:
        g = pd.DataFrame({"warn": warn, "obs": obs, "day": days.to_numpy()})
        out["CSI_ci95"] = boot_ci(g, "day", lambda x: scores(contingency(x["warn"].to_numpy(), x["obs"].to_numpy())), n=500)["CSI"]
    return out


def best_threshold(p: np.ndarray, y: np.ndarray) -> float:
    grid = np.unique(np.quantile(p, np.linspace(0.5, 0.995, 120)))
    csi = [scores(contingency(p >= t, y))["CSI"] for t in grid]
    return float(grid[int(np.nanargmax(csi))])


def hybrid_district_days() -> pd.DataFrame:
    W = RESULTS_DIR / "warning_levels"
    frames = [pd.read_csv(W / f"{s}_warning_levels.csv", usecols=["district", "datetime", "tier"], parse_dates=["datetime"]) for s in ("validation", "test", "replay")]
    w = pd.concat(frames)
    w["day"] = w["datetime"].dt.normalize()
    return w.groupby(["district", "day"])["tier"].agg(lambda s: max(s.map(RANK))).rename("hybrid_rank").reset_index()


def external(pred: pd.DataFrame, flag: str) -> dict:
    ev = pd.read_csv(PROJECT_ROOT / "data/external/labels/labels_2022_2025.csv", parse_dates=["date", "end_date"])
    end = pd.read_parquet(CLEANED_DIR / "flood_inventory_cleaned.parquet")["start_datetime"].max()
    ev = ev[ev["date"] > end]
    idx = pred.set_index(["district", "day"])[flag]
    hits = []
    for _, e in ev.iterrows():
        days = pd.date_range(e["date"] - pd.Timedelta(days=1), e["end_date"])
        v = [idx.get((e["district"], t)) for t in days]
        v = [x for x in v if x is not None and x == x]
        if v:
            hits.append(bool(max(v)))
    rng = np.random.default_rng(RANDOM_STATE)
    b = rng.choice(np.array(hits, float), (2000, len(hits))).mean(1) if hits else np.array([np.nan])
    near = set()
    for _, e in ev.iterrows():
        for t in pd.date_range(e["date"] - pd.Timedelta(days=2), e["end_date"] + pd.Timedelta(days=2)):
            near.add((e["district"], t))
    a = pred[(pred[flag] == 1) & pred["day"].dt.month.between(6, 9) & (pred["day"] > end)]
    burden = [{"monsoon": int(y), "alert_district_days": len(g), "share_near_event": round(float(np.mean([(x, t) in near for x, t in zip(g["district"], g["day"])])), 3)}
              for y, g in a.groupby(a["day"].dt.year)]
    return {"events_scored": len(hits), "detected": int(sum(hits)), "POD": round(float(np.mean(hits)), 3) if hits else None,
            "ci95": [round(float(np.percentile(b, 2.5)), 3), round(float(np.percentile(b, 97.5)), 3)], "alert_burden": burden}


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    d = build()
    d.to_parquet(OUT / "dataset.parquet", index=False)
    tr = d[(d["day"] < pd.Timestamp(TRAIN_END_DATE)) & d["y"].notna()]
    va = d[(d["day"] >= pd.Timestamp(TRAIN_END_DATE)) & (d["day"] < pd.Timestamp(VAL_END_DATE)) & d["y"].notna()]
    te = d[(d["day"] >= pd.Timestamp(VAL_END_DATE)) & d["y"].notna()]
    print({k: (len(x), int(x["y"].sum())) for k, x in (("train", tr), ("validation", va), ("test", te))})

    fitted, val_pr = {}, {}
    for name, m in models(tr["y"]).items():
        fitted[name] = m.fit(tr[FEATURES], tr["y"].astype(int))
        val_pr[name] = round(average_precision_score(va["y"], m.predict_proba(va[FEATURES])[:, 1]), 4)
    best = max(val_pr, key=val_pr.get)
    m = fitted[best]
    thr = best_threshold(m.predict_proba(va[FEATURES])[:, 1], va["y"].to_numpy())
    d["p"] = m.predict_proba(d[FEATURES])[:, 1]
    d["alert"] = (d["p"] >= thr).astype(int)

    hy = hybrid_district_days()
    d = d.merge(hy, on=["district", "day"], how="left")
    d["hybrid_alert"] = np.where(d["hybrid_rank"].notna(), (d["hybrid_rank"] >= RANK["ALERT"]).astype(float), np.nan)
    te = d[(d["day"] >= pd.Timestamp(VAL_END_DATE)) & d["y"].notna()]
    common = te[te["hybrid_alert"].notna()]

    res = {"model": best, "validation_pr_auc": val_pr, "threshold": round(thr, 4),
           "counts": {k: {"district_days": len(x), "positives": int(x["y"].sum())} for k, x in (("train", tr), ("validation", va), ("test", te))},
           "test_all": {"roc_auc": round(roc_auc_score(te["y"], te["p"]), 3), "pr_auc": round(average_precision_score(te["y"], te["p"]), 3),
                        "base_rate": round(te["y"].mean(), 3), "brier": round(brier_score_loss(te["y"], te["p"]), 4),
                        **cat(te["alert"].to_numpy(), te["y"].to_numpy(), te["day"])},
           "test_common_with_hybrid": {"district_days": len(common),
                                       "district_day_model": cat(common["alert"].to_numpy(), common["y"].to_numpy(), common["day"]),
                                       "hybrid": cat(common["hybrid_alert"].to_numpy().astype(bool), common["y"].to_numpy(), common["day"])},
           "test_v2_truth": cat(te["alert"].to_numpy(), te["y_v2"].to_numpy()),
           "external_district_day_model": external(d, "alert"),
           "external_hybrid": external(d, "hybrid_alert"),
           "coverage": {"district_days_with_any_gauge": int(((d["n_cwc"] > 0) | (d["n_hm"] > 0)).sum()), "district_days": len(d),
                        "replay_days_without_cwc": int(((d["n_cwc"] == 0) & (d["day"] > pd.Timestamp(VAL_END_DATE))).sum())}}
    if best == "logistic":
        coef = m.named_steps["clf"].coef_[0]
        res["coefficients"] = dict(sorted(zip(FEATURES, np.round(coef, 3).tolist()), key=lambda kv: -abs(kv[1])))
    a, b = res["test_common_with_hybrid"]["district_day_model"], res["test_common_with_hybrid"]["hybrid"]
    xa, xb = res["external_district_day_model"], res["external_hybrid"]
    burden = lambda x: next((r["alert_district_days"] for r in x["alert_burden"] if r["monsoon"] == 2024), 0)  # noqa: E731
    res["decision"] = {"csi_ok": (a["CSI"] or 0) >= (b["CSI"] or 0), "external_pod_ok": (xa["POD"] or 0) >= (xb["POD"] or 0),
                       "burden_ok": burden(xa) <= burden(xb)}
    res["decision"]["adopt"] = all(res["decision"].values())
    d[["district", "day", "p", "alert", "y", "y_v2", "hybrid_alert", "n_cwc", "n_hm", "rain_cwc_max", "rain_hm_max", "era5_max"]].to_csv(OUT / "predictions.csv", index=False)
    (OUT / "summary.json").write_text(json.dumps(res, indent=2, default=str))
    print(json.dumps(res, indent=1, default=str))
    return res


if __name__ == "__main__":
    run()
