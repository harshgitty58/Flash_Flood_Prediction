"""
Phase 1 — industry-standard forecast verification (WMO-style).

Two evaluation units:
  station-hour  : every reporting gauge-hour (harsh; what the ML model is trained on)
  district-day  : one warning per district per calendar day = highest tier of its gauges over the label window
                  (day D-1 00:00 → day D 23:59, matching the "flood today or tomorrow" target);
                  observed = a flood recorded in that district on day D. This is how warnings are issued and judged.

Scores (at ≥ ALERT and ≥ SEVERE): POD, FAR, POFD, CSI, ETS (Gilbert skill), HSS, frequency bias.
Probabilistic: Brier, Brier Skill Score vs climatology (training base rate per month), reliability diagram, ECE.
Uncertainty: 95 % CIs from a block bootstrap over days (whole days resampled, keeping same-day hours together).
Baselines: climatology (never warn), persistence (flood yesterday → warn today), rainfall-rule only,
           district prior only (always warn in historically flood-prone districts), ML only, hybrid (deployed).
Also: honest lead time (first sustained switch-on), relative economic value (cost-loss), breakdowns.

Run: python -m src.verification   (after src.warning_levels)
"""
import json

import numpy as np
import pandas as pd

from src.config import CLEANED_DIR
from src.data_loader import load_ml_dataset
from src.model_config import RANDOM_STATE, RESULTS_DIR, TARGET_COL

OUT = RESULTS_DIR / "verification"
RANK = {"NORMAL": 0, "WATCH": 1, "ALERT": 2, "SEVERE": 3, "EXTREME": 4}
N_BOOT = 1000


# ---------------------------------------------------------------------------- scores
def contingency(warn: np.ndarray, obs: np.ndarray) -> dict:
    warn, obs = warn.astype(bool), obs.astype(bool)
    tp, fp = int((warn & obs).sum()), int((warn & ~obs).sum())
    fn, tn = int((~warn & obs).sum()), int((~warn & ~obs).sum())
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def scores(c: dict) -> dict:
    tp, fp, fn, tn = c["tp"], c["fp"], c["fn"], c["tn"]
    n = tp + fp + fn + tn
    div = lambda a, b: float(a / b) if b else float("nan")  # noqa: E731
    hits_random = (tp + fp) * (tp + fn) / n if n else 0.0
    hss_den = (tp + fn) * (fn + tn) + (tp + fp) * (fp + tn)
    return {
        "POD": div(tp, tp + fn), "FAR": div(fp, tp + fp), "POFD": div(fp, fp + tn),
        "CSI": div(tp, tp + fp + fn), "ETS": div(tp - hits_random, tp + fp + fn - hits_random),
        "HSS": div(2 * (tp * tn - fp * fn), hss_den), "bias": div(tp + fp, tp + fn),
    }


def boot_ci(df: pd.DataFrame, block: str, fn, n=N_BOOT, seed=RANDOM_STATE) -> dict:
    """Block bootstrap: resample whole blocks (days) with replacement; return 2.5/97.5 % for each score."""
    rng = np.random.default_rng(seed)
    groups = {k: g.index.to_numpy() for k, g in df.groupby(block)}
    keys = np.array(list(groups))
    out = []
    for _ in range(n):
        idx = np.concatenate([groups[k] for k in rng.choice(keys, len(keys), replace=True)])
        out.append(fn(df.loc[idx]))
    res = pd.DataFrame(out)
    return {k: [round(float(np.nanpercentile(res[k], 2.5)), 3), round(float(np.nanpercentile(res[k], 97.5)), 3)] for k in res}


def verify(df: pd.DataFrame, warn_col: str, obs_col: str, block: str, level: int) -> dict:
    f = lambda d: scores(contingency(d[warn_col].to_numpy() >= level, d[obs_col].to_numpy()))  # noqa: E731
    point = f(df)
    ci = boot_ci(df, block, f)
    return {**contingency(df[warn_col].to_numpy() >= level, df[obs_col].to_numpy()),
            **{k: (round(v, 3) if v == v else None) for k, v in point.items()}, "ci95": ci}


def brier_block(p: np.ndarray, y: np.ndarray, clim: np.ndarray) -> dict:
    bs, bs_ref = float(np.mean((p - y) ** 2)), float(np.mean((clim - y) ** 2))
    return {"brier": round(bs, 5), "brier_climatology": round(bs_ref, 5), "BSS": round(1 - bs / bs_ref, 4) if bs_ref else None}


def reliability(p: np.ndarray, y: np.ndarray, bins=10) -> tuple[list, float]:
    """Quantile-binned reliability curve + expected calibration error."""
    edges = np.unique(np.quantile(p, np.linspace(0, 1, bins + 1)))
    idx = np.clip(np.searchsorted(edges, p, side="right") - 1, 0, len(edges) - 2)
    rows, ece = [], 0.0
    for b in range(len(edges) - 1):
        m = idx == b
        if m.sum() == 0:
            continue
        mp, fo = float(p[m].mean()), float(y[m].mean())
        rows.append({"bin": b, "mean_pred": round(mp, 4), "obs_freq": round(fo, 4), "n": int(m.sum())})
        ece += m.mean() * abs(mp - fo)
    return rows, round(float(ece), 4)


def relative_value(H: float, F: float, s: float) -> list[dict]:
    """Relative economic value (Richardson 2000) over cost/loss ratios α."""
    out = []
    for a in np.round(np.linspace(0.01, 0.99, 50), 3):
        den = min(a, s) - s * a
        v = (min(a, s) - F * a * (1 - s) + H * s * (1 - a) - s) / den if den else float("nan")
        out.append({"alpha": float(a), "value": round(float(v), 4)})
    return out


# ---------------------------------------------------------------------------- data
def load_hours() -> pd.DataFrame:
    W = RESULTS_DIR / "warning_levels"
    parts = []
    for split in ("validation", "test"):
        d = pd.read_csv(W / f"{split}_warning_levels.csv", parse_dates=["datetime"])
        d["split"] = split
        parts.append(d)
    h = pd.concat(parts, ignore_index=True)
    for c in ("tier", "tier_ml", "tier_rain"):
        h[c + "_r"] = h[c].map(RANK)
    h["day"] = h["datetime"].dt.normalize()
    h[TARGET_COL] = h[TARGET_COL].astype(int)
    return h


def climatology(h: pd.DataFrame) -> tuple[np.ndarray, pd.Series, set]:
    """Base rate per month from the TRAINING split only (no peeking), and flood-prone districts from training."""
    split = json.loads((RESULTS_DIR / "splits.json").read_text())
    ds = load_ml_dataset()
    tr = ds[(ds[TARGET_COL].notna()) & (ds["datetime"] <= split["train"]["end"])]
    month_rate = tr.groupby(tr["datetime"].dt.month)[TARGET_COL].mean()
    overall = tr[TARGET_COL].mean()
    clim = h["datetime"].dt.month.map(month_rate).fillna(overall).to_numpy()
    by_district = tr.groupby("district")[TARGET_COL].mean()
    prone = set(by_district[by_district >= by_district.median()].index)
    return clim, by_district, prone


def district_days(h: pd.DataFrame, prone: set) -> pd.DataFrame:
    inv = pd.read_parquet(CLEANED_DIR / "flood_inventory_cleaned.parquet")
    flood_days = set(zip(inv["district"], inv["start_datetime"].dt.normalize()))
    rows = []
    for (dist, day), _ in h.groupby(["district", "day"]):
        w = h[(h["district"] == dist) & (h["day"] >= day - pd.Timedelta(days=1)) & (h["day"] <= day)]
        rows.append({"district": dist, "day": day, "split": w["split"].iloc[-1],
                     "tier_r": w["tier_r"].max(), "tier_ml_r": w["tier_ml_r"].max(), "tier_rain_r": w["tier_rain_r"].max(),
                     "p_max": w["p_calibrated"].max(), "obs": int((dist, day) in flood_days),
                     "persist": int((dist, day - pd.Timedelta(days=1)) in flood_days),
                     "prior_r": RANK["ALERT"] if dist in prone else 0})
    return pd.DataFrame(rows)


def honest_lead_times(h: pd.DataFrame) -> pd.DataFrame:
    """First sustained (≥ 3 h) switch-on to ≥ ALERT in the 48 h before an event, ignoring alarms already on
    24 h before the window opens (those are district baselines, not warnings)."""
    inv = pd.read_parquet(CLEANED_DIR / "flood_inventory_cleaned.parquet")
    inv = inv[(inv["start_datetime"] >= h["datetime"].min()) & (inv["start_datetime"] <= h["datetime"].max())]
    rows = []
    for _, e in inv.drop_duplicates(["district", "start_datetime"]).iterrows():
        D = e["start_datetime"].normalize()
        g = h[(h["district"] == e["district"]) & (h["datetime"] >= D - pd.Timedelta(hours=72)) & (h["datetime"] < D + pd.Timedelta(days=1))]
        if g.empty:
            continue
        status, lead = "missed", None
        for st, s in g.sort_values("datetime").groupby("station"):
            pre = s[(s["datetime"] >= D - pd.Timedelta(hours=72)) & (s["datetime"] < D - pd.Timedelta(hours=48))]
            already_on = len(pre) and (pre["tier_r"] >= 2).mean() > 0.5
            win = s[s["datetime"] >= D - pd.Timedelta(hours=48)].set_index("datetime")["tier_r"] >= 2
            sustained = win.rolling(3).sum() >= 3
            if sustained.any():
                t_on = sustained[sustained].index[0] - pd.Timedelta(hours=2)
                if already_on:
                    status = "baseline (already on)" if status == "missed" else status
                    continue
                h_before = (D - t_on).total_seconds() / 3600
                if lead is None or h_before > lead:
                    lead, status = h_before, "warned"
        rows.append({"district": e["district"], "event_day": D.date(), "status": status,
                     "lead_h_before_event_day": round(lead, 1) if lead is not None else None})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------- run
def run():
    OUT.mkdir(parents=True, exist_ok=True)
    h = load_hours()
    clim, by_district, prone = climatology(h)
    h["clim"] = clim
    h["persist_r"] = 0  # hour-level persistence is undefined without hourly event times
    h["prior_r"] = np.where(h["district"].isin(prone), RANK["ALERT"], 0)
    dd = district_days(h, prone)

    layers = {"hybrid (deployed)": "tier_r", "ML only": "tier_ml_r", "rainfall rule only": "tier_rain_r",
              "district prior only": "prior_r"}
    out = {"definitions": __doc__.split("Run:")[0].strip(), "units": {}}
    table = []
    for unit, df, obs, block in (("station-hour", h, TARGET_COL, "day"), ("district-day", dd, "obs", "day")):
        for split in ("validation", "test", "both"):
            d = df if split == "both" else df[df["split"] == split]
            d = d.reset_index(drop=True)
            base_rate = float(d[obs].mean())
            ls = dict(layers)
            if unit == "district-day":
                d = d.assign(persist_r=d["persist"] * RANK["ALERT"])
                ls["persistence (flood yesterday)"] = "persist_r"
            for lvl_name, lvl in (("≥ ALERT", 2), ("≥ SEVERE", 3)):
                for name, col in ls.items():
                    if lvl_name == "≥ SEVERE" and name in ("district prior only", "persistence (flood yesterday)"):
                        continue
                    r = verify(d, col, obs, block, lvl)
                    table.append({"unit": unit, "split": split, "level": lvl_name, "layer": name, "n": len(d),
                                  "events": int(d[obs].sum()), "base_rate": round(base_rate, 4), **r})
    out["contingency"] = table
    tbl = pd.DataFrame(table)
    tbl.drop(columns=["ci95"]).to_csv(OUT / "contingency_scores.csv", index=False)

    # probabilistic skill (hour level uses calibrated p; district-day uses max p over the window)
    y = h[TARGET_COL].to_numpy()
    prob = {"station-hour": brier_block(h["p_calibrated"].to_numpy(), y, h["clim"].to_numpy())}
    # No calibrated *daily* probability exists yet (max of hourly probabilities is not one), so a district-day BSS
    # would be meaningless; it arrives with the Phase 4 district-day model.
    prob["district-day"] = {"note": "not computed: no calibrated daily probability yet (Phase 4 district-day model)"}
    rel, ece = reliability(h["p_calibrated"].to_numpy(), y)
    prob["reliability_station_hour"], prob["ECE_station_hour"] = rel, ece
    out["probabilistic"] = prob

    # honest lead time
    lt = honest_lead_times(h)
    lt.to_csv(OUT / "honest_lead_times.csv", index=False)
    warned = lt[lt["status"] == "warned"]
    out["lead_time"] = {"events": int(len(lt)), "warned_before": int(len(warned)),
                        "baseline_only": int((lt["status"] == "baseline (already on)").sum()), "missed": int((lt["status"] == "missed").sum()),
                        "median_lead_h": float(warned["lead_h_before_event_day"].median()) if len(warned) else None,
                        "events_table": lt.astype(object).where(lt.notna(), None).to_dict("records")}

    # relative economic value of the deployed warning (district-day, ≥ ALERT, both months)
    hy = tbl[(tbl.unit == "district-day") & (tbl.split == "both") & (tbl.level == "≥ ALERT") & (tbl.layer == "hybrid (deployed)")].iloc[0]
    s = float(dd["obs"].mean())
    out["relative_value"] = relative_value(hy["POD"], hy["POFD"], s)

    # breakdowns (district-day, ≥ ALERT, hybrid)
    def brk(col):
        rows = []
        for k, g in dd.groupby(col):
            c = contingency(g["tier_r"].to_numpy() >= 2, g["obs"].to_numpy())
            rows.append({col: str(k), "days": len(g), "events": int(g["obs"].sum()), **c, **{m: (round(v, 3) if v == v else None) for m, v in scores(c).items()}})
        return rows
    dd["month"] = dd["day"].dt.strftime("%Y-%m")
    out["breakdown_district"], out["breakdown_month"] = brk("district"), brk("month")

    (OUT / "verification.json").write_text(json.dumps(out, indent=2, default=str))
    show = tbl[(tbl.split == "both")][["unit", "level", "layer", "events", "POD", "FAR", "CSI", "ETS", "HSS", "bias"]]
    print(show.to_string(index=False)); print(json.dumps({k: v for k, v in prob.items() if not k.startswith("reliability")}))
    print(out["lead_time"] | {"events_table": "…"})
    return out


if __name__ == "__main__":
    run()
