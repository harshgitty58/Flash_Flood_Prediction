"""
L8 — tune the station-local rainfall-tier rule on validation to cut false alarms (LABELS_PLAN.md §0, next levers).

Why: rain_24h is a rolling sum, so one heavy shower keeps a gauge at ALERT for up to 24 h after the rain has
stopped, and every gauge alerts on its own. The hybrid's FAR (~0.8-0.9) is driven by that rainfall layer.

Search space (declared up front, 32 rules; the deployed rule is the first one):
  alert_24h       rain_24h (mm) needed for the rainfall ALERT level        64.5 (IMD heavy), 80, 100, 115.6
  fresh_6h        rainfall ALERT+ only while rain_6h >= this (mm); cloudburst (rain_1h >= 100) is always exempt
                  0 (off), 5, 10, 20
  susceptibility  ±1 level from landslide hotspot × district flood-severity                 on / off
Objective: district-day CSI of the HYBRID tier (max of ML and rainfall) at >= ALERT on the validation month, v1 labels.
Ties -> fewer alert district-days. Adoption: the best candidate replaces the default only if the lower bound of its
validation CSI 95 % CI exceeds the default's CSI (with ~15 event-days a month, smaller differences are noise).
The test month is only reported, never used for the choice. The rule stays
station-local so the backend can apply it to a single /predict call.
Output: results/warning_levels/rain_rule.json (read by src.warning_levels), rain_rule_search.csv
Run: python -m src.tier_tuning   (after src.warning_levels; then re-run src.warning_levels)
"""
import itertools
import json

import numpy as np
import pandas as pd

from src.data_loader import load_ml_dataset
from src.model_config import RESULTS_DIR, TARGET_COL
from src.verification import boot_ci, contingency, scores
from src.warning_levels import DEFAULT_RULE, TIERS, rain_tier_index

W = RESULTS_DIR / "warning_levels"
CTX = ["rain_1h", "rain_6h", "rain_24h", "is_landslide_hotspot", "district_flood_severity_index"]
GRID = [{"alert_24h": a, "fresh_6h": f, "susceptibility": s}
        for a, f, s in itertools.product([64.5, 80.0, 100.0, 115.6], [0.0, 5.0, 10.0, 20.0], [True, False])]


def dd_scores(d: pd.DataFrame, hybrid: np.ndarray, ci=False) -> dict:
    g = d.assign(warn=hybrid >= TIERS.index("ALERT"), day=d["datetime"].dt.normalize())
    g = g.groupby(["district", "day"]).agg(warn=("warn", "max"), obs=(TARGET_COL, "max")).reset_index()
    c = contingency(g["warn"].to_numpy(), g["obs"].to_numpy())
    out = {**c, **{k: round(v, 3) for k, v in scores(c).items()}, "alert_dd": int(g["warn"].sum())}
    if ci:
        f = lambda x: scores(contingency(x["warn"].to_numpy(), x["obs"].to_numpy()))  # noqa: E731
        out["CSI_ci95"] = boot_ci(g, "day", f, n=500)["CSI"]
    return out


def run():
    ctx = load_ml_dataset()[["station", "datetime"] + CTX]
    dfsi_median = float(ctx["district_flood_severity_index"].median())
    sets = {}
    for split in ("validation", "test"):
        d = pd.read_csv(W / f"{split}_warning_levels.csv", parse_dates=["datetime"]).merge(ctx, on=["station", "datetime"], how="left")
        sets[split] = (d, d["tier_ml"].map(TIERS.index).to_numpy())
    rows = []
    for rule in GRID:
        rec = {**rule}
        for split, (d, ml) in sets.items():
            s = dd_scores(d, np.maximum(ml, rain_tier_index(d, dfsi_median, rule)))
            rec.update({f"{split}_{k}": s[k] for k in ("POD", "FAR", "CSI", "HSS", "alert_dd")})
        rows.append(rec)
    res = pd.DataFrame(rows)
    res.to_csv(W / "rain_rule_search.csv", index=False)
    best = res.sort_values(["validation_CSI", "validation_alert_dd"], ascending=[False, True]).iloc[0]
    chosen = {"alert_24h": float(best["alert_24h"]), "fresh_6h": float(best["fresh_6h"]), "susceptibility": bool(best["susceptibility"])}

    report = {}
    for name, rule in (("deployed_before", DEFAULT_RULE), ("tuned", chosen)):
        report[name] = {split: dd_scores(d, np.maximum(ml, rain_tier_index(d, dfsi_median, rule)), ci=True) for split, (d, ml) in sets.items()}
    adopted = report["tuned"]["validation"]["CSI_ci95"][0] > report["deployed_before"]["validation"]["CSI"]
    out = {"rule": chosen if adopted else DEFAULT_RULE, "adopted": bool(adopted), "best_candidate": chosen, "default_rule": DEFAULT_RULE,
           "adoption_rule": "best candidate's validation CSI CI lower bound > default validation CSI", "objective": "validation district-day CSI, hybrid >= ALERT, v1 labels",
           "grid_size": len(GRID), "district_day_scores": report}
    (W / "rain_rule.json").write_text(json.dumps(out, indent=2, default=str))
    print(res.sort_values("validation_CSI", ascending=False).head(8).to_string(index=False))
    print(json.dumps({k: out[k] for k in ("rule", "adopted", "best_candidate")}, default=str))
    return out


if __name__ == "__main__":
    run()
