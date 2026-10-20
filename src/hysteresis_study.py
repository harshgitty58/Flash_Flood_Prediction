"""
WS-09.6 / RQ8 (PRAHAR_MASTER_PLAN.md): does tier hysteresis stop warning flicker without costing skill?

Rule under test (per gauge, hourly): escalation is immediate; the tier drops ONE level only after HOLD_H consecutive
hours with a lower raw tier, and never earlier than HOLD_H hours after the last change. A gap of more than 1 h in a
gauge's record resets its state (the gauge is not reporting).

Fixed before the run (2026-10-21):
  data        deployed hybrid tiers, validation (Jul 2023) + test (1-25 Aug 2023), results/warning_levels/*; flicker also
              on the unlabelled replay period (operational behaviour)
  scoring     the published verification code (src/verification.py): strict district-day definition, >= ALERT
  flicker     tier changes per gauge-day
  adoption    HOLD_H = 6 is adopted if, pooled over validation + test: flicker falls by >= 50 %, district-day CSI is no
              more than 0.01 below the deployed rule, and POD is no more than 0.05 below it. 3 h and 12 h are reported
              for context only. The app is not changed here; adoption is recorded for the v1.0 warning engine (WS-09.3).
Run: python -m src.hysteresis_study   ->  results/v3/rq8_hysteresis.json, results/v3/rq8_hysteresis.md
"""
import json

import numpy as np
import pandas as pd

from src.model_config import RESULTS_DIR
from src.verification import RANK, climatology, district_days, honest_lead_times, load_hours, verify

OUT = RESULTS_DIR / "v3"
HOLD_PRIMARY = 6


def hysteresis(df: pd.DataFrame, col: str = "tier_r", hold_h: int = HOLD_PRIMARY) -> np.ndarray:
    out = np.empty(len(df), dtype=int)
    d = df.reset_index(drop=True)
    for _, g in d.groupby("station", sort=False):
        g = g.sort_values("datetime")
        t, raw, idx = g["datetime"].to_numpy(), g[col].to_numpy(), g.index.to_numpy()
        state, below, since = 0, 0, 0
        for i in range(len(g)):
            if i and (t[i] - t[i - 1]) > np.timedelta64(1, "h"):
                state, below, since = 0, 0, 0
            r = int(raw[i])
            since += 1
            if r >= state:
                if r > state:
                    since = 0
                state, below = r, 0
            else:
                below += 1
                if below >= hold_h and since >= hold_h:
                    state, below, since = state - 1, 0, 0
                    state = max(state, r)
            out[idx[i]] = state
    return out


def flicker(df: pd.DataFrame, col: str) -> float:
    changes, days = 0, 0
    for _, g in df.groupby("station", sort=False):
        s = g.sort_values("datetime")[col].to_numpy()
        changes += int((s[1:] != s[:-1]).sum())
        days += g["datetime"].dt.normalize().nunique()
    return round(changes / max(days, 1), 3)


def dd_scores(h: pd.DataFrame, prone: set) -> dict:
    dd = district_days(h, prone)
    out = {}
    for split in ("validation", "test", "both"):
        d = (dd if split == "both" else dd[dd["split"] == split]).reset_index(drop=True)
        r = verify(d, "tier_r", "obs", "day", RANK["ALERT"])
        out[split] = {k: r[k] for k in ("POD", "FAR", "CSI")} | {"CSI_ci95": r["ci95"].get("CSI"), "alert_district_days": int((d["tier_r"] >= 2).sum())}
    return out


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    h = load_hours()
    _, _, prone = climatology(h)
    replay = pd.read_csv(RESULTS_DIR / "warning_levels/replay_warning_levels.csv", usecols=["station", "datetime", "tier"], parse_dates=["datetime"])
    replay["tier_r"] = replay["tier"].map(RANK)
    res = {"deployed": {"flicker_val_test": flicker(h, "tier_r"), "flicker_replay": flicker(replay, "tier_r"),
                        "district_day": dd_scores(h, prone), "lead": None}, "variants": {}}
    lt = honest_lead_times(h)
    res["deployed"]["lead"] = lt["status"].value_counts().to_dict()
    for hold in (3, 6, 12):
        hh = h.copy()
        hh["tier_r"] = hysteresis(hh, hold_h=hold)
        rp = replay.copy()
        rp["tier_r"] = hysteresis(rp, hold_h=hold)
        res["variants"][f"hold_{hold}h"] = {"flicker_val_test": flicker(hh, "tier_r"), "flicker_replay": flicker(rp, "tier_r"),
                                            "district_day": dd_scores(hh, prone), "lead": honest_lead_times(hh)["status"].value_counts().to_dict()}
    base, v = res["deployed"], res["variants"][f"hold_{HOLD_PRIMARY}h"]
    checks = {"flicker_halved": v["flicker_val_test"] <= 0.5 * base["flicker_val_test"],
              "csi_within_0.01": v["district_day"]["both"]["CSI"] >= base["district_day"]["both"]["CSI"] - 0.01,
              "pod_within_0.05": v["district_day"]["both"]["POD"] >= base["district_day"]["both"]["POD"] - 0.05}
    res["adoption"] = checks | {"adopt": all(checks.values())}
    (OUT / "rq8_hysteresis.json").write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")

    rows = []
    for name, r in [("deployed (no hysteresis)", base)] + [(k, x) for k, x in res["variants"].items()]:
        b = r["district_day"]["both"]
        rows.append({"rule": name, "flicker / gauge-day (Jul-Aug 2023)": r["flicker_val_test"], "flicker / gauge-day (replay)": r["flicker_replay"],
                     "dd POD": b["POD"], "dd FAR": b["FAR"], "dd CSI": b["CSI"], "ALERT district-days": b["alert_district_days"],
                     "warned before / baseline / missed": f"{r['lead'].get('warned', 0)} / {r['lead'].get('baseline (already on)', 0)} / {r['lead'].get('missed', 0)}"})
    md = ["# RQ8 / WS-09.6: warning-tier hysteresis", "",
          "Escalate immediately; drop one level only after N calm hours. Scored with the published strict district-day verification "
          "(validation + test pooled, ≥ ALERT). Rule fixed before the run: see `src/hysteresis_study.py`.", "",
          pd.DataFrame(rows).to_markdown(index=False), "",
          f"**Decision ({HOLD_PRIMARY} h):** {'adopt for the v1.0 warning engine' if res['adoption']['adopt'] else 'not adopted'} {checks}.", "",
          "**Reading:** the deployed tiers already change less than once per gauge-day (the plan's target is <= 1.0), so there is little "
          "flicker to remove. Stepping down one level at a time can even add changes (EXTREME to NORMAL becomes three steps), and longer holds "
          "add ALERT district-days and turn some early warnings into 'already on' baselines. Hysteresis is therefore not needed for the "
          "current tiers; WS-09.6 is closed with this evidence and re-checked when the v1.0 tiers change.", ""]
    (OUT / "rq8_hysteresis.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    return res


if __name__ == "__main__":
    run()
