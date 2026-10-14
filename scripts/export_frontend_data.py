"""Export real pipeline outputs to static JSON for the FloodGuard web app.

Usage: python scripts/export_frontend_data.py [--replay "2026-09-05 19:00"]
Everything shown in the UI must come from here — no hard-coded metrics in the frontend.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "web" / "public" / "data"
MODEL = "xgboost"

TIERS = [(0.75, "EXTREME"), (0.5, "SEVERE"), (0.3, "ALERT"), (0.15, "WATCH"), (0.0, "NORMAL")]

MODALITY = {
    "Rainfall": ["rain_1h", "rain_3h", "rain_6h", "rain_12h", "rain_24h", "rain_48h", "rain_72h",
                 "rain_max_intensity_24h", "rain_intensity_change_1h", "api_decay_85"],
    "River discharge": ["discharge_clean", "discharge_change_1h", "discharge_change_3h", "discharge_anomaly"],
    "Landslide / terrain": ["dist_to_nearest_landslide_km", "landslide_count_5km", "landslide_count_10km",
                            "is_landslide_hotspot"],
    "Flood history": ["historical_flood_count_prior_t", "days_since_last_flood_prior_t",
                      "district_flood_severity_index", "district_flooded_area_pct",
                      "district_historical_fatalities", "district_mean_flood_duration_days", "district_population"],
    "Season / time": ["hour_of_day", "day_of_week", "day_of_year", "month", "is_monsoon"],
    "Location (lat/lon)": ["latitude", "longitude"],
}

EXPERIMENTS = {
    "Exp_A_Rainfall_Only": "Rainfall only",
    "Exp_B_Rainfall_Discharge": "+ River discharge",
    "Exp_C_Rainfall_Discharge_FloodHist": "+ Flood history",
    "Exp_D_Rainfall_Discharge_Flood_Landslide": "+ Landslide / terrain",
    "Exp_E_Full_Multimodal": "+ Season & lat/lon",
    "Exp_F_No_Location": "Full minus lat/lon",
    "Exp_G_Static_History": "Static history (deployed)",
}


def tier(p):
    return next(name for cut, name in TIERS if p >= cut)


def clean(v):
    if isinstance(v, (float, np.floating)):
        return None if np.isnan(v) else round(float(v), 4)
    if isinstance(v, np.integer):
        return int(v)
    return v


def strict(o):
    """Recursively replace NaN/inf with None so the output is valid JSON (browsers reject bare NaN)."""
    if isinstance(o, float):
        return None if (o != o or o in (float("inf"), float("-inf"))) else o
    if isinstance(o, dict):
        return {k: strict(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [strict(v) for v in o]
    if hasattr(o, "item"):  # numpy scalar
        return strict(o.item())
    return o


def dump(name, obj):
    obj = json.loads(json.dumps(obj, default=clean))  # serialise numpy etc. first
    (OUT / name).write_text(json.dumps(strict(obj), allow_nan=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {name}")


def records(df):
    return [{k: clean(v) for k, v in r.items()} for r in df.to_dict("records")]


def main(replay):
    from src.data_loader import FEATURE_EXPERIMENTS, FINAL_EXPERIMENT  # noqa: E402
    OUT.mkdir(parents=True, exist_ok=True)
    T = pd.Timestamp(replay) if replay != "auto" else None

    ds = pd.read_parquet(ROOT / "data/processed/final/uttarakhand_flash_flood_ml_dataset.parquet")
    ds = ds.drop_duplicates(["station", "datetime"])
    # held-out test + unlabelled-period inference (after flood-inventory coverage) = full replay timeline
    # Phase 4 outputs: calibrated probability (Venn-Abers), conformal set/confidence, warning tier
    pred = pd.concat([pd.read_csv(ROOT / f"results/warning_levels/{k}_warning_levels.csv", parse_dates=["datetime"])
                      for k in ("test", "replay")])
    pred = pred.rename(columns={"predicted_probability": "raw_score"}).rename(columns={"p_calibrated": "predicted_probability"})
    pred = pred.drop_duplicates(["station", "datetime"]).sort_values("datetime")
    if replay == "auto":  # hour where the most stations sit at high hybrid tiers (ties → higher calibrated prob.)
        rank = {"NORMAL": 0, "WATCH": 1, "ALERT": 2, "SEVERE": 3, "EXTREME": 4}
        pred["tier_rank"] = pred["tier"].map(rank)
        per_hour = pred.groupby("datetime").agg(severe=("tier_rank", lambda x: int((x >= 3).sum())),
                                                alert=("tier_rank", lambda x: int((x >= 2).sum())), p=("predicted_probability", "max"))
        T = per_hour.sort_values(["severe", "alert", "p"], ascending=False).index[0]
        print("auto replay time:", T)
    river = pd.read_csv(ROOT / "curated_dataset/river_discharge/cwc_uttarakhand_river_station_summary.csv")
    ls = pd.read_csv(ROOT / "curated_dataset/landslide/uttarakhand_landslide_inventory_cleaned.csv")
    inv = pd.read_csv(ROOT / "curated_dataset/flood_inventory/uttarakhand_flood_inventory_curated.csv")
    inv_end = pd.to_datetime(inv["Start_Date"]).max()

    # stations
    st = ds.groupby("station")[["district", "latitude", "longitude"]].first().reset_index()
    stations = records(st.rename(columns={"latitude": "lat", "longitude": "lon"}).assign(kind="rain"))
    stations += records(river[["station", "district", "latitude", "longitude"]]
                        .rename(columns={"latitude": "lat", "longitude": "lon"}).assign(kind="river"))
    dump("stations.json", stations)

    # snapshot: latest prediction per station in the 24 h before T
    win = pred[(pred.datetime <= T) & (pred.datetime > T - pd.Timedelta(hours=24))]
    last = win.sort_values("datetime").groupby("station").tail(1)
    last = last.merge(ds, on=["station", "datetime", "district"], how="left", suffixes=("", "_ds"))
    shp = pd.read_csv(ROOT / "results/shap/shap_top_drivers.csv", parse_dates=["datetime"]).drop(columns="district")
    last = last.merge(shp, on=["station", "datetime"], how="left")
    snap = []
    for _, r in last.iterrows():
        p = float(r.predicted_probability)
        snap.append({
            "station": r.station, "district": r.district, "time": r.datetime.isoformat(),
            "p": round(p, 4), "tier": r.tier, "predicted": int(r.predicted_class), "raw_score": round(float(r.raw_score), 4),
            "confidence": round(float(r.confidence), 3), "credibility": round(float(r.credibility), 3), "cp_set_90": r.cp_set_90,
            "tier_ml": r.get("tier_ml"), "tier_rain": r.get("tier_rain"), "trigger": r.get("trigger"),
            "drivers": [{"feature": r[f"driver_{k}"], "shap": clean(r[f"shap_{k}"]), "value": clean(r[f"value_{k}"])}
                        for k in (1, 2, 3) if isinstance(r.get(f"driver_{k}"), str)], "observed": None if pd.isna(r.flood_event_24h) else int(r.flood_event_24h),
            "signals": {k: clean(r.get(k)) for k in ["rain_1h", "rain_6h", "rain_24h", "rain_72h",
                                                    "rain_max_intensity_24h", "api_decay_85", "discharge_anomaly",
                                                    "dist_to_nearest_landslide_km", "landslide_count_10km",
                                                    "historical_flood_count_prior_t", "district_flood_severity_index"]},
        })
    order = {"EXTREME": 4, "SEVERE": 3, "ALERT": 2, "WATCH": 1, "NORMAL": 0}
    # rank by the final (hybrid) tier first, so rainfall-triggered SEVERE stations are not buried under WATCH ones
    snap.sort(key=lambda s: (-order.get(s["tier"], 0), -s["p"], -(s["signals"].get("rain_24h") or 0)))

    prev = pred[(pred.datetime <= T - pd.Timedelta(hours=3)) & (pred.datetime > T - pd.Timedelta(hours=27))]
    prev_max = float(prev.sort_values("datetime").groupby("station").tail(1).predicted_probability.max()) if len(prev) else None

    win_ds = ds[(ds.datetime <= T) & (ds.datetime > T - pd.Timedelta(hours=24))]
    sources = [
        {"name": "Rainfall gauges", "status": "available" if len(win_ds) else "missing",
         "detail": f"{win_ds.station.nunique()}/{st.shape[0]} stations reporting (24 h)"},
        {"name": "River discharge", "status": "available" if win_ds.discharge_clean.notna().any() else "missing",
         "detail": f"{int(win_ds.discharge_clean.notna().sum())} readings joined (24 h)"},
        {"name": "Landslide inventory", "status": "available", "detail": f"{len(ls):,} GSI records (static)"},
        {"name": "Flood history", "status": "available", "detail": f"{len(inv)} IMD events + district indices"},
        {"name": "DEM / terrain", "status": "pending", "detail": "not yet ingested into model"},
        {"name": "Satellite precipitation", "status": "pending", "detail": "not yet ingested into model"},
    ]
    dump("snapshot.json", {
        "replay_time": T.isoformat(), "model": f"XGBoost · {EXPERIMENTS[FINAL_EXPERIMENT]} · {len(FEATURE_EXPERIMENTS[FINAL_EXPERIMENT])} features",
        "base_rate": json.loads((ROOT / "results/warning_levels/warning_thresholds.json").read_text())["base_rate"],
        "conformal": json.loads((ROOT / "results/conformal/cp_summary.json").read_text()),
        "peak_p": snap[0]["p"] if snap else None, "peak_p_3h_ago": prev_max,
        "stations_reporting": len(snap), "stations_total": int(st.shape[0]),
        "tier_counts": {t: sum(s["tier"] == t for s in snap) for _, t in TIERS},
        "stations": snap, "sources": sources,
    })

    # timeline: hourly regional max/mean probability, T-72h .. T+24h
    tl = pred[(pred.datetime >= T - pd.Timedelta(hours=72)) & (pred.datetime <= T + pd.Timedelta(hours=24))]
    tl = tl.groupby("datetime").agg(max_p=("predicted_probability", "max"), mean_p=("predicted_probability", "mean"),
                                    q90=("predicted_probability", lambda x: x.quantile(0.9)),
                                    q10=("predicted_probability", lambda x: x.quantile(0.1)),
                                    n=("station", "nunique"), observed=("flood_event_24h", "max")).reset_index()
    tl["t"] = tl.datetime.dt.strftime("%Y-%m-%dT%H:%M")
    dump("timeline.json", records(tl.drop(columns="datetime")))

    # model
    cmp_ = pd.read_csv(ROOT / "results/model_evaluation/model_comparison.csv")
    fus = pd.read_csv(ROOT / "results/event_cv/event_cv_summary.csv")
    fus["label"] = fus.experiment.map(EXPERIMENTS)
    fus["final"] = fus.experiment == FINAL_EXPERIMENT
    imp = pd.read_csv(ROOT / "results/shap/shap_global_importance.csv").rename(columns={"mean_abs_shap": "importance"})
    imp["importance"] = imp["importance"] / imp["importance"].sum()  # share of total mean |SHAP|
    group = {f: g for g, fs in MODALITY.items() for f in fs}
    imp["group"] = imp.feature.map(group).fillna("Other")
    grouped = imp.groupby("group").importance.sum().sort_values(ascending=False)
    dump("model.json", {
        "comparison": records(cmp_[["model", "threshold", "val_roc_auc", "val_pr_auc", "val_f1", "val_recall",
                                    "val_precision", "test_roc_auc", "test_pr_auc", "test_f1", "test_recall",
                                    "test_precision", "val_brier", "test_brier"]]),
        "final_experiment": EXPERIMENTS[FINAL_EXPERIMENT],
        "lead": json.loads((ROOT / "results/event_cv/event_lead_summary.json").read_text()),
        "robustness": records(pd.read_csv(ROOT / "results/robustness/robustness_summary.csv")),
        "coverage": records(pd.read_csv(ROOT / "results/data_audit/coverage_matrix.csv").rename(columns={"Unnamed: 0": "month"})),
        "windows": json.loads((ROOT / "results/data_windows.json").read_text()),
        "splits": json.loads((ROOT / "results/splits.json").read_text()),
        "normalization": json.loads((ROOT / "results/preprocessing/normalization_params.json").read_text()),
        "warning": json.loads((ROOT / "results/warning_levels/warning_thresholds.json").read_text()),
        "fusion": records(fus[["label", "features", "folds", "positives", "pooled_roc_auc", "pooled_pr_auc",
                               "base_rate", "mean_fold_roc_auc", "min_fold_roc_auc", "final"]]),
        "importance": records(imp[["feature", "importance", "group"]].head(15)),
        "importance_groups": [{"group": g, "importance": round(float(v), 4)} for g, v in grouped.items()],
        "dataset": {"rows": int(len(ds)), "stations": int(st.shape[0]), "districts": int(ds.district.nunique()),
                    "start": ds.datetime.min().isoformat(), "end": ds.datetime.max().isoformat(),
                    "positives": int(ds.flood_event_24h.sum()), "labelled_rows": int(ds.flood_event_24h.notna().sum()),
                    "label_end": inv_end.isoformat(),
                    "landslides": int(len(ls)), "flood_events": int(len(inv))},
    })

    dump("metrics.json", json.loads((ROOT / "results/metrics/metrics.json").read_text()))
    print("wrote metrics.json")

    # events
    inv = inv.rename(columns={"Start_Date": "start", "Main Cause": "cause", "Districts": "districts",
                              "Human fatality": "fatalities", "Latitude": "lat", "Longitude": "lon"})
    inv["start"] = inv.start.str[:10]
    dump("events.json", {
        "floods": records(inv[["UEI", "start", "cause", "districts", "fatalities", "lat", "lon"]]),
        "landslides_by_district": ls.district.value_counts().to_dict(),
        "landslide_points": [[round(a, 3), round(b, 3)] for a, b in ls[["longitude", "latitude"]].dropna().values],
    })

    # E3 ranking view: districts to watch on the replay day (a ranking, not a warning)
    sc, e3 = ROOT / "results/model_upgrade/e3_district_scores.csv", ROOT / "results/model_upgrade/e3_district_pooled.json"
    if sc.exists() and e3.exists():
        s3 = pd.read_csv(sc, parse_dates=["day"])
        day = s3.loc[s3["day"] <= pd.Timestamp(T).replace(tzinfo=None).normalize(), "day"].max()
        top = s3[s3["day"] == day].sort_values("p", ascending=False)
        dump("district_watch.json", {"day": str(day.date()), "recall_at_3": json.loads(e3.read_text())["ranking_recall_at_3"],
                                     "ranking": [{"district": r.district, "score": round(float(r.p), 4), "rank": i + 1} for i, r in enumerate(top.itertuples())]})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", default="auto", help='"auto" or "YYYY-MM-DD HH:MM"')
    main(ap.parse_args().replay)
