"""
Objective 4D — Operational warning tiers (hybrid).

Final tier = max(ML tier, rainfall tier); the layer that set it is recorded in `trigger`.

ML tier — Venn-Abers calibrated probability (src/conformal.py); cut-offs = 2× / 5× / 10× / 20× the calibration base rate.
A conformal FLOOD singleton at 90 % lifts the ML tier to at least ALERT.

Rainfall tier — IMD rainfall categories on the station's own gauge, adjusted for terrain/history susceptibility:
  rain level: moderate rain_24h ≥ 15.6 → 1, heavy ≥ 64.5 → 2, very heavy ≥ 115.6 → 3,
              extremely heavy ≥ 204.5 mm/24 h or cloudburst rain_1h ≥ 100 mm/h → 4
  (the ALERT threshold and a 'fresh rain in the last 6 h' condition are tuned on validation: src/tier_tuning.py)
  susceptibility: +1 if the station is a landslide hotspot AND its district flood-severity index ≥ median,
                  −1 if neither, else 0.  (moderate rain alone never exceeds WATCH)
This layer is a transparent rule, not a learned model: it makes real cloudbursts register even though the
district-date labels cannot teach the rain → flood link (rainfall-only ROC-AUC ≈ 0.5 in event CV).

Run: python -m src.warning_levels   (after src.conformal)
"""
import json

import numpy as np
import pandas as pd

from src.data_loader import load_ml_dataset
from src.model_config import RESULTS_DIR, TARGET_COL

CONF_DIR = RESULTS_DIR / "conformal"
OUT_DIR = RESULTS_DIR / "warning_levels"
TIERS = ["NORMAL", "WATCH", "ALERT", "SEVERE", "EXTREME"]
# ML cut-offs are multiples of the calibration-set base rate, so they stay meaningful when the calibration month
# changes (a fixed 1 % WATCH sat below the calibrated floor once calibration moved to the July monsoon).
LIFT = {"WATCH": 2, "ALERT": 5, "SEVERE": 10, "EXTREME": 20}


def thresholds_for(base_rate: float) -> dict:
    return {t: round(min(0.95, k * base_rate), 5) for t, k in LIFT.items()}
IMD_24H = {"moderate": 15.6, "heavy": 64.5, "very_heavy": 115.6, "extremely_heavy": 204.5}
CLOUDBURST_1H = 100.0
CONTEXT = ["rain_1h", "rain_6h", "rain_24h", "is_landslide_hotspot", "district_flood_severity_index"]


def ml_tier_index(df: pd.DataFrame, thresholds: dict) -> np.ndarray:
    p = df["p_calibrated"].to_numpy()
    idx = np.zeros(len(df), dtype=int)
    for i, t in enumerate(TIERS[1:], start=1):
        idx[p >= thresholds[t]] = i
    return np.where(df["cp_set_90"].to_numpy() == "FLOOD", np.maximum(idx, TIERS.index("ALERT")), idx)


# Station-local rainfall rule. DEFAULT_RULE is the original IMD-category rule; src.tier_tuning searches a small grid on
# validation (district-day CSI) and writes results/warning_levels/rain_rule.json, which run() and the backend then use.
DEFAULT_RULE = {"alert_24h": IMD_24H["heavy"], "fresh_6h": 0.0, "susceptibility": True}
RULE_FILE = OUT_DIR / "rain_rule.json"


def load_rule() -> dict:
    return {**DEFAULT_RULE, **(json.loads(RULE_FILE.read_text())["rule"] if RULE_FILE.exists() else {})}


def rain_tier_index(df: pd.DataFrame, dfsi_median: float, rule: dict | None = None) -> np.ndarray:
    rule = {**DEFAULT_RULE, **(rule or {})}
    r24, r1 = df["rain_24h"].fillna(0).to_numpy(), df["rain_1h"].fillna(0).to_numpy()
    heavy = rule["alert_24h"]
    burst = (r24 >= IMD_24H["extremely_heavy"]) | (r1 >= CLOUDBURST_1H)
    level = np.select([burst, r24 >= max(IMD_24H["very_heavy"], heavy), r24 >= heavy, r24 >= IMD_24H["moderate"]], [4, 3, 2, 1], 0)
    if rule["fresh_6h"] > 0 and "rain_6h" in df:
        # rain_24h stays high for a day after a shower: without fresh rain in the last 6 h, cap at WATCH
        stale = (df["rain_6h"].fillna(0).to_numpy() < rule["fresh_6h"]) & ~burst
        level = np.where(stale, np.minimum(level, 1), level)
    hot = df["is_landslide_hotspot"].fillna(0).to_numpy() == 1
    severe_district = df["district_flood_severity_index"].fillna(dfsi_median).to_numpy() >= dfsi_median
    adj = np.where(hot & severe_district, 1, np.where(~hot & ~severe_district, -1, 0)) if rule["susceptibility"] else 0
    idx = np.where(level >= 2, np.clip(level + adj, 1, 4), level)  # moderate rain stays WATCH
    return idx.astype(int)


def assign(df: pd.DataFrame, dfsi_median: float, thresholds: dict, rule: dict | None = None) -> pd.DataFrame:
    ml, rn = ml_tier_index(df, thresholds), rain_tier_index(df, dfsi_median, rule)
    df["tier_ml"], df["tier_rain"] = np.array(TIERS)[ml], np.array(TIERS)[rn]
    df["tier"] = np.array(TIERS)[np.maximum(ml, rn)]
    df["trigger"] = np.select([np.maximum(ml, rn) == 0, ml >= rn], ["none", "ml"], "rainfall")
    return df


def tier_table(d: pd.DataFrame, col: str, base_rate: float, split: str) -> list[dict]:
    rows = []
    for t in TIERS:
        g = d[d[col] == t]
        rows.append({"split": split, "layer": col, "tier": t, "rows": len(g), "flood_rows": int(g[TARGET_COL].sum()),
                     "hit_rate": round(g[TARGET_COL].mean(), 4) if len(g) else None,
                     "lift_vs_base": round(g[TARGET_COL].mean() / base_rate, 2) if len(g) else None})
    return rows


def alert_stats(d: pd.DataFrame, col: str) -> dict:
    alert = d[col].isin(["ALERT", "SEVERE", "EXTREME"])
    y = d[TARGET_COL].astype(int)
    tp, fp, fn = int((alert & (y == 1)).sum()), int((alert & (y == 0)).sum()), int((~alert & (y == 1)).sum())
    prec, rec = tp / max(1, tp + fp), tp / max(1, tp + fn)
    return {"precision": round(prec, 3), "recall": round(rec, 3), "f1": round(2 * prec * rec / max(1e-9, prec + rec), 3),
            "false_alarm_rate": round(fp / max(1, int((y == 0).sum())), 4), "alerts": int(alert.sum())}


def run():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ctx = load_ml_dataset()[["station", "datetime"] + CONTEXT]
    dfsi_median = float(ctx["district_flood_severity_index"].median())
    load = lambda f: pd.read_csv(f, parse_dates=["datetime"]).merge(ctx, on=["station", "datetime"], how="left")  # noqa: E731
    test, replay = load(CONF_DIR / "cp_test_predictions.csv"), load(CONF_DIR / "cp_replay_predictions.csv")
    cal = pd.read_csv(CONF_DIR / "calibration_scores.csv")
    val = pd.read_csv(RESULTS_DIR / "predictions" / "validation_xgboost.csv", parse_dates=["datetime"]).merge(ctx, on=["station", "datetime"], how="left")
    val["p_calibrated"], val["cp_set_90"] = cal["p_calibrated"].values, "UNCERTAIN"
    base_rate = float(cal["y"].mean())  # calibration-set base rate
    thr = thresholds_for(base_rate)
    rule = load_rule()
    for d in (val, test, replay):
        assign(d, dfsi_median, thr, rule)
    test.drop(columns=CONTEXT).to_csv(OUT_DIR / "test_warning_levels.csv", index=False)
    val.drop(columns=[c for c in CONTEXT if c in val]).to_csv(OUT_DIR / "validation_warning_levels.csv", index=False)
    replay.drop(columns=CONTEXT).to_csv(OUT_DIR / "replay_warning_levels.csv", index=False)

    rows = []
    for name, d in (("validation", val), ("test", test)):
        for col in ("tier_ml", "tier_rain", "tier"):
            rows += tier_table(d, col, base_rate, name)
    conf = pd.DataFrame(rows)
    conf.to_csv(OUT_DIR / "warning_level_confusion.csv", index=False)

    layers = {f"{s}_{col}": alert_stats(d, col) for s, d in (("validation", val), ("test", test)) for col in ("tier_ml", "tier_rain", "tier")}
    stats = {"base_rate": round(base_rate, 5), "lift": LIFT, "thresholds": thr, "imd_24h_mm": IMD_24H, "cloudburst_1h_mm": CLOUDBURST_1H, "rain_rule": rule,
             "dfsi_median": dfsi_median, "alert_level": layers,
             "test_alert_recall": layers["test_tier"]["recall"], "test_alert_precision": layers["test_tier"]["precision"],
             "test_false_alarm_rate": layers["test_tier"]["false_alarm_rate"],
             "replay_tier_counts": replay["tier"].value_counts().reindex(TIERS, fill_value=0).to_dict(),
             "replay_trigger_counts": replay["trigger"].value_counts().to_dict()}
    (OUT_DIR / "warning_thresholds.json").write_text(json.dumps(stats, indent=2))
    md = ["# Warning-level design rationale (hybrid)", "", __doc__.split("Run:")[0].strip(), "",
          f"Base rate (labelled data): {base_rate:.2%}.", "", "## ≥ ALERT as a classifier (per layer)", "",
          pd.DataFrame(layers).T.to_markdown(), "", "## Tier vs observed", "", conf.to_markdown(index=False)]
    (OUT_DIR / "warning_design_rationale.md").write_text("\n".join(md), encoding="utf-8")
    print(pd.DataFrame(layers).T.to_string()); print(stats["replay_tier_counts"], stats["replay_trigger_counts"])


if __name__ == "__main__":
    run()
