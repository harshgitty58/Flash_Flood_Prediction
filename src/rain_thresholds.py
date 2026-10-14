"""
E2 (MODEL_UPGRADE_PLAN.md) — rainfall thresholds fitted on documented events (flash-flood-guidance style).

Event rainfall: for each documented event (labels_2022_2025.csv, confidence >= medium) the district's max daily rain
over [day-1, last day] from CWC gauges, else USDMA hydromet (ERA5-only events are skipped: reanalysis under-reads
convective rain), for 24 h and 3-day totals (results/district_day/dataset.parquet).
Fit set: events 2022-02 → 2023-07 and all of 2024. Held out: the Aug 2023 test month and all 2025 events.
Groups: plains (Haridwar, Udham Singh Nagar) vs hills; a group with < 8 fit events uses the pooled thresholds.
Tiers (fixed before the run): ALERT = 20th, SEVERE = 50th, EXTREME = 80th percentile of event rainfall, for 24 h and
72 h separately (level = the higher of the two); cloudburst rain_1h >= 100 mm stays EXTREME; moderate rain
(>= 15.6 mm/24 h) stays WATCH. Applied station-locally to rain_24h / rain_72h, hybrid = max(ML tier, rain tier).

Adoption rule: test-month hybrid district-day CSI >= current, AND 2025-event POD >= current, AND ALERT district-days
in monsoons 2024 and 2025 <= current.
Output: results/model_upgrade/e2_thresholds.json
Run: python -m src.rain_thresholds   (after src.district_day)
"""
import json

import numpy as np
import pandas as pd

from src.config import PROJECT_ROOT
from src.data_loader import load_ml_dataset
from src.model_config import RESULTS_DIR, VAL_END_DATE
from src.tier_tuning import dd_scores
from src.warning_levels import CLOUDBURST_1H, DEFAULT_RULE, IMD_24H, TIERS, rain_tier_index

OUT = RESULTS_DIR / "model_upgrade"
PLAINS = {"Haridwar", "Udham Singh Nagar"}
PCT = {"ALERT": 20, "SEVERE": 50, "EXTREME": 80}
W = RESULTS_DIR / "warning_levels"


def event_rain() -> pd.DataFrame:
    d = pd.read_parquet(RESULTS_DIR / "district_day/dataset.parquet").set_index(["district", "day"])
    ev = pd.read_csv(PROJECT_ROOT / "data/external/labels/labels_2022_2025.csv", parse_dates=["date", "end_date"])
    ev = ev[ev["date_confidence"] != "low"]
    rows = []
    for _, e in ev.iterrows():
        x = d.loc[[(e["district"], t) for t in pd.date_range(e["date"] - pd.Timedelta(days=1), e["end_date"]) if (e["district"], t) in d.index]]
        if x.empty:
            continue
        src = "cwc" if (x["n_cwc"] > 0).any() else ("hydromet" if (x["n_hm"] > 0).any() else None)
        if src is None:
            continue
        c = "rain_cwc_max" if src == "cwc" else "rain_hm_max"
        rows.append({"district": e["district"], "date": e["date"], "source": src, "r24": x[c].max(), "r72": x[f"{c}_3d"].max()})
    return pd.DataFrame(rows)


def fit(er: pd.DataFrame) -> dict:
    fit_m = ((er["date"] >= "2022-02-01") & (er["date"] < "2023-08-01")) | (er["date"].dt.year == 2024)
    f = er[fit_m]
    pooled = {w: {t: round(float(np.percentile(f[w], q)), 1) for t, q in PCT.items()} for w in ("r24", "r72")}
    out = {"n_fit_events": int(len(f)), "pooled": pooled}
    for g, m in (("plains", f["district"].isin(PLAINS)), ("hills", ~f["district"].isin(PLAINS))):
        out[g] = ({w: {t: round(float(np.percentile(f.loc[m, w], q)), 1) for t, q in PCT.items()} for w in ("r24", "r72")}
                  if m.sum() >= 8 else pooled) | {"n": int(m.sum())}
    return out


def rain_tier_fitted(df: pd.DataFrame, th: dict) -> np.ndarray:
    lvl = np.where(df["rain_24h"].fillna(0) >= IMD_24H["moderate"], 1, 0)
    plains = df["district"].isin(PLAINS).to_numpy()
    for i, t in enumerate(("ALERT", "SEVERE", "EXTREME"), start=2):
        t24 = np.where(plains, th["plains"]["r24"][t], th["hills"]["r24"][t])
        t72 = np.where(plains, th["plains"]["r72"][t], th["hills"]["r72"][t])
        hit = (df["rain_24h"].fillna(0).to_numpy() >= t24) | (df["rain_72h"].fillna(0).to_numpy() >= t72)
        lvl = np.where(hit, i, lvl)
    return np.where(df["rain_1h"].fillna(0).to_numpy() >= CLOUDBURST_1H, 4, lvl).astype(int)


def external(rep: pd.DataFrame, hyb: np.ndarray) -> dict:
    a = rep.assign(alert=hyb >= TIERS.index("ALERT"), day=rep["datetime"].dt.normalize()).groupby(["district", "day"])["alert"].max()
    ev = pd.read_csv(PROJECT_ROOT / "data/external/labels/labels_2022_2025.csv", parse_dates=["date", "end_date"])
    ev25 = ev[ev["date"].dt.year == 2025]
    hits = [bool(max(a.get((e["district"], t), False) for t in pd.date_range(e["date"] - pd.Timedelta(days=1), e["end_date"])))
            for _, e in ev25.iterrows() if any((e["district"], t) in a.index for t in pd.date_range(e["date"] - pd.Timedelta(days=1), e["end_date"]))]
    al = a[a & a.index.get_level_values("day").month.isin([6, 7, 8, 9])]
    yrs = al.index.get_level_values("day").year
    return {"pod_2025": f"{sum(hits)}/{len(hits)}", "pod_2025_value": round(float(np.mean(hits)), 3) if hits else None,
            "alert_dd": {int(y): int((yrs == y).sum()) for y in (2024, 2025)}}


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    er = event_rain()
    th = fit(er)
    ctx = load_ml_dataset()[["station", "datetime", "rain_1h", "rain_6h", "rain_24h", "rain_72h", "is_landslide_hotspot", "district_flood_severity_index"]]
    dfsi = float(ctx["district_flood_severity_index"].median())
    load = lambda s: pd.read_csv(W / f"{s}_warning_levels.csv", parse_dates=["datetime"]).merge(ctx, on=["station", "datetime"], how="left")  # noqa: E731
    te, rep = load("test"), load("replay")
    res = {"thresholds_mm": th, "event_rain_by_source": er["source"].value_counts().to_dict()}
    for name, fn in (("current", lambda x: rain_tier_index(x, dfsi, DEFAULT_RULE)), ("fitted", lambda x: rain_tier_fitted(x, th))):
        hy_te = np.maximum(te["tier_ml"].map(TIERS.index).to_numpy(), fn(te))
        hy_rep = np.maximum(rep["tier_ml"].map(TIERS.index).to_numpy(), fn(rep))
        res[name] = {"test_dd": dd_scores(te, hy_te, ci=True), **external(rep, hy_rep)}
    c, f = res["current"], res["fitted"]
    res["decision"] = {"csi_ok": f["test_dd"]["CSI"] >= c["test_dd"]["CSI"],
                       "pod_2025_ok": (f["pod_2025_value"] or 0) >= (c["pod_2025_value"] or 0),
                       "burden_ok": all(f["alert_dd"][y] <= c["alert_dd"][y] for y in (2024, 2025))}
    res["decision"]["adopt"] = all(res["decision"].values())
    (OUT / "e2_thresholds.json").write_text(json.dumps(res, indent=2, default=str))
    print(json.dumps({"thresholds": th, **{k: {"CSI": res[k]["test_dd"]["CSI"], "POD": res[k]["test_dd"]["POD"], "FAR": res[k]["test_dd"]["FAR"],
                                               "pod_2025": res[k]["pod_2025"], "alert_dd": res[k]["alert_dd"]} for k in ("current", "fitted")},
                      "decision": res["decision"]}, indent=1))
    return res


if __name__ == "__main__":
    run()
