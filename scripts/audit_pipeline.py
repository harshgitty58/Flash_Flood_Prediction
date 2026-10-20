"""End-to-end lineage audit: raw data → cleaned → features → models → predictions → Phase 4 → web JSON → frontend.

Checks that every stage exists, is newer than its inputs (not stale), and agrees with the previous stage.
Run: python scripts/audit_pipeline.py
"""
import glob
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.cleaning import parse_cwc_timestamp  # noqa: E402
from src.data_loader import FEATURE_EXPERIMENTS, FINAL_EXPERIMENT  # noqa: E402

FAILS, WARNS = [], []


def ok(msg): print(f"  OK    {msg}")
def warn(msg): WARNS.append(msg); print(f"  WARN  {msg}")
def fail(msg): FAILS.append(msg); print(f"  FAIL  {msg}")
def mtime(p): return datetime.fromtimestamp(Path(p).stat().st_mtime)


def newer(child, *parents, label="", tol_s=600):
    """child must not be older than its inputs; tol_s allows artefacts written in the same run a few seconds apart
    (train_pipeline writes predictions just before it saves the model file)."""
    c = mtime(child)
    for p in parents:
        if Path(p).exists() and (mtime(p) - c).total_seconds() > tol_s:
            fail(f"STALE {label or Path(child).name}: older than {Path(p).name} ({c:%m-%d %H:%M} < {mtime(p):%m-%d %H:%M})")
            return False
    return True


def main():
    print("\n[1] RAW DATASETS")
    raw = sorted(glob.glob(str(ROOT / "curated_dataset/cwc_rainfall_uttarakhand/*.csv")))
    d = pd.concat([pd.read_csv(f) for f in raw])
    t = parse_cwc_timestamp(d["Data Acquisition Time"])
    rate = t.notna().mean()
    (ok if rate > 0.999 else fail)(f"rainfall: {len(d):,} rows in {len(raw)} files, timestamp parse rate {rate:.2%}")
    sent = (d["Telemetry Hourly Rainfall (mm)"] == 511.5).sum()
    ok(f"rainfall sentinel 511.5 rows present in raw: {sent} (must be removed in cleaning)")
    for f in ["river_discharge/cwc_uttarakhand_river_discharge_curated_hourly.csv", "landslide/uttarakhand_landslide_inventory_cleaned.csv",
              "flood_inventory/uttarakhand_flood_inventory_curated.csv"]:
        p = ROOT / "curated_dataset" / f
        (ok if p.exists() else fail)(f"{f}: {'%s rows' % f'{len(pd.read_csv(p)):,}' if p.exists() else 'MISSING'}")

    print("\n[2] CLEANED → FEATURES → FINAL TABLE")
    cl = ROOT / "data/processed/cleaned/rainfall_cleaned.parquet"
    c = pd.read_parquet(cl)
    newer(cl, *raw)
    man = ROOT / "curated_dataset/MANIFEST.sha256"
    pins = [ln.split("  ", 1) for ln in man.read_text(encoding="utf-8").splitlines() if ln]
    pin_ok = all(hashlib.sha256((ROOT / "curated_dataset" / rel).read_bytes()).hexdigest() == h for h, rel in pins)
    (ok if pin_ok else fail)(f"curated_dataset/ matches MANIFEST.sha256 ({len(pins)} raw files pinned; the pipeline reads this single copy)")
    kept = c["rainfall_quality_flag"].value_counts().to_dict()
    (ok if len(c) > 0.85 * t.notna().sum() - 25000 else fail)(f"rainfall_cleaned: {len(c):,} rows, flags {kept}")
    (ok if (c.loc[c.rainfall_quality_flag == 'valid', 'rainfall_clean'] <= 150).all() else fail)("no valid reading above 150 mm/h")
    fin = ROOT / "data/processed/final/uttarakhand_flash_flood_ml_dataset.parquet"
    ds = pd.read_parquet(fin)
    newer(fin, cl)
    dup = ds.duplicated(["station", "datetime"]).sum()
    (ok if dup == 0 else fail)(f"final table: {len(ds):,} rows, {ds.station.nunique()} stations, duplicates {dup}")
    gaps = ds.sort_values(["station", "datetime"]).groupby("station")["datetime"].diff().dt.total_seconds().div(3600).dropna()
    odd = gaps[(gaps > 1) & (gaps < 7 * 24)]  # anything between 1 h and the offline limit means a broken grid
    (ok if odd.empty else fail)(f"hourly grid: contiguous within segments; {int((gaps > 1).sum())} offline gaps removed (min {gaps[gaps > 1].min() if (gaps > 1).any() else 0:.0f} h)")
    lab = ds["flood_event_24h"].notna()
    ok(f"labelled {lab.sum():,} rows ({lab.mean():.1%}), positives {int(ds.flood_event_24h.sum())}, label end {ds.loc[lab, 'datetime'].max()}")
    miss = [f for f in FEATURE_EXPERIMENTS[FINAL_EXPERIMENT] if f not in ds]
    (ok if not miss else fail)(f"final feature set '{FINAL_EXPERIMENT}' ({len(FEATURE_EXPERIMENTS[FINAL_EXPERIMENT])} cols) present" + (f" — missing {miss}" if miss else ""))
    r24 = ds["rain_24h"]
    ok(f"rain_24h: median {r24.median():.1f}, p99 {r24.quantile(.99):.1f}, max {r24.max():.1f} mm")

    print("\n[3] TRAINED MODELS")
    for m in ["xgboost", "random_forest", "logistic_regression"]:
        p = ROOT / f"models/{m}/model.joblib"
        if not p.exists():
            fail(f"{m}: model.joblib missing"); continue
        mdl = joblib.load(p)
        names = list(getattr(mdl, "feature_names_in_", []))
        same = names == FEATURE_EXPERIMENTS[FINAL_EXPERIMENT]
        if newer(p, fin, label=f"{m} model") and same:
            ok(f"{m}: {len(names)} features match final set, trained {mtime(p):%m-%d %H:%M}")
        elif not same:
            fail(f"{m}: feature names do not match final set ({len(names)} vs {len(FEATURE_EXPERIMENTS[FINAL_EXPERIMENT])})")
        meta = ROOT / f"models/{m}/metadata.json"
        if meta.exists():
            md = json.loads(meta.read_text())
            ok(f"{m} metadata: train {md.get('train_range') or md.get('train_start')} · feature_set {md.get('feature_set')}")

    print("\n[4] PREDICTIONS")
    for k in ["validation", "test", "replay"]:
        p = ROOT / f"results/predictions/{k}_xgboost.csv"
        if not p.exists():
            fail(f"{k}_xgboost.csv missing"); continue
        newer(p, ROOT / "models/xgboost/model.joblib")
        pr = pd.read_csv(p, parse_dates=["datetime"])
        ok(f"{k}: {len(pr):,} rows, {pr.station.nunique()} stations, {pr.datetime.min():%Y-%m-%d} → {pr.datetime.max():%Y-%m-%d}, score {pr.predicted_probability.min():.2f}–{pr.predicted_probability.max():.2f}")
    rp = ROOT / "results/predictions/replay_xgboost.csv"
    if rp.exists():
        n = len(pd.read_csv(rp, usecols=["station"]))
        (ok if abs(n - (~lab).sum()) < 10 else fail)(f"replay rows {n:,} vs unlabelled rows in final table {(~lab).sum():,}")

    print("\n[5] PHASE 4 OUTPUTS")
    chain = [("results/preprocessing/normalization_params.json", fin), ("results/splits.json", fin),
             ("results/metrics/metrics.json", ROOT / "results/warning_levels/replay_warning_levels.csv"),
             ("results/event_cv/event_cv_summary.csv", fin), ("results/conformal/cp_replay_predictions.csv", rp),
             ("results/warning_levels/replay_warning_levels.csv", ROOT / "results/conformal/cp_replay_predictions.csv"),
             ("results/shap/shap_top_drivers.csv", ROOT / "models/xgboost/model.joblib"),
             ("results/robustness/robustness_summary.csv", ROOT / "models/xgboost/model.joblib"),
             ("data/external/labels/labels_2022_2025.csv", ROOT / "data/external/labels/sitreps_manual.csv"),
             ("data/external/labels/labels_2022_2025.csv", ROOT / "curated_dataset/flood_inventory/supplement_2024_2025.csv"),
             ("results/labels/label_audit.json", ROOT / "data/external/labels/labels_daily.csv"),
             ("results/labels/label_experiment.json", ROOT / "data/external/labels/labels_daily.csv"),
             ("results/metrics/external_validation.json", ROOT / "data/external/labels/labels_2022_2025.csv")]
    for f, parent in chain:
        p = ROOT / f
        if not p.exists():
            fail(f"{f} missing")
        elif newer(p, parent):
            ok(f"{f} ({mtime(p):%m-%d %H:%M})")

    print("\n[6] BACKEND EXPORT (web/public/data)")
    W = ROOT / "web/public/data"
    for f in ["stations.json", "snapshot.json", "timeline.json", "model.json", "events.json", "impact.json",
              "landmarks.geojson", "metrics.json", "system.json", "bld/index.json"]:
        p = W / f
        (ok if p.exists() else fail)(f"{f}: {p.stat().st_size / 1e6:.2f} MB, {mtime(p):%m-%d %H:%M}" if p.exists() else f"{f} missing")
    bad_json = []
    for f in list(W.glob("*.json")) + list(W.glob("*.geojson")):
        try:
            json.loads(f.read_text(encoding="utf-8"), parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
        except ValueError as e:
            bad_json.append(f"{f.name}: {e}")
    (ok if not bad_json else fail)("all exported files are strict JSON (no NaN/Infinity)" + (f" — {bad_json}" if bad_json else ""))
    snap = json.loads((W / "snapshot.json").read_text())
    newer(W / "snapshot.json", ROOT / "results/warning_levels/replay_warning_levels.csv", label="snapshot.json")
    ok(f"snapshot: replay {snap['replay_time']}, model '{snap['model']}', tiers {snap['tier_counts']}, reporting {snap['stations_reporting']}/{snap['stations_total']}")
    imp = json.loads((W / "impact.json").read_text())
    (ok if imp.get("replay_time") == snap["replay_time"] else fail)(f"impact layer replay {imp.get('replay_time')} vs snapshot {snap['replay_time']}")
    stn = {s["station"] for s in json.loads((W / "stations.json").read_text())}
    bad = [s["station"] for s in snap["stations"] if s["station"] not in stn]
    (ok if not bad else fail)(f"all snapshot stations exist in stations.json" + (f" — unknown {bad}" if bad else ""))

    print("\n[7] FRONTEND")
    src = "\n".join(Path(p).read_text(encoding="utf-8") for p in glob.glob(str(ROOT / "web/src/**/*.tsx"), recursive=True))
    used = set(re.findall(r"useData<[^>]+>\('(\w+)'\)", src))
    missing = [u for u in used if not ((W / f"{u}.json").exists() or (W / f"{u}.geojson").exists())]
    (ok if not missing else fail)(f"data names used by pages {sorted(used)} all exported" + (f" — missing {missing}" if missing else ""))
    tidx = json.loads((W / "bld/index.json").read_text())["tiles"]
    missing_t = [t for t in tidx if not (W / "bld" / str(t["z"]) / str(t["x"]) / f"{t['y']}.json").exists()]
    (ok if not missing_t else fail)(f"{len(tidx)} building tiles indexed, all present; largest {max(t['bytes'] for t in tidx) / 1e3:.0f} KB")
    newer(W / "bld/index.json", ROOT / "results/impact/buildings.geojson", label="building tiles")
    (ok if not (W / "buildings.geojson").exists() else fail)("full buildings.geojson not shipped in the web bundle (tiles only)")
    for a in ["prahar-mark.png", "favicon.png"]:
        (ok if (ROOT / "web/public" / a).exists() else fail)(f"asset {a}")

    print(f"\nRESULT: {len(FAILS)} fail, {len(WARNS)} warn")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
