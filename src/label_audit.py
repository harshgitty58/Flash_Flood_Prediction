"""
Label audit — IMD inventory (training labels v1) vs SANDRP compilations on the period both cover (LABELS_PLAN.md §5).

Unit: district-day, ±1 day tolerance (night-time events are often reported on the next day).
  imd_matched     IMD days that SANDRP also reports
  sandrp_only     SANDRP days with no IMD record within ±1 day → likely false negatives in the v1 labels
  imd_only        IMD days SANDRP does not track (often plains / riverine floods; SANDRP lists cloudbursts)
For the validation/test months it also checks whether the deployed hybrid tiers alerted (>= ALERT) on SANDRP-only
days, i.e. alerts that the v1 labels currently score as false alarms.

Decision gate: SANDRP-only events >= GATE_SHARE × IMD events → build label v2 and test it as a separate experiment.
Run: python -m src.label_audit   (after scripts/build_labels.py)
"""
import json

import pandas as pd

from src.config import PROJECT_ROOT
from src.model_config import RESULTS_DIR, TRAIN_END_DATE, VAL_END_DATE

LAB = PROJECT_ROOT / "data/external/labels"
OUT = RESULTS_DIR / "labels"
GATE_SHARE = 0.25
LABEL_START, LABEL_END = pd.Timestamp("2022-02-01"), pd.Timestamp("2023-08-25")  # Window A, labelled rows
SANDRP_SEASONS = [(pd.Timestamp("2022-05-01"), pd.Timestamp("2022-10-31")), (pd.Timestamp("2023-06-01"), pd.Timestamp("2023-09-30"))]
RANK = {"NORMAL": 0, "WATCH": 1, "ALERT": 2, "SEVERE": 3, "EXTREME": 4}


def in_overlap(d: pd.Series) -> pd.Series:
    m = (d >= LABEL_START) & (d <= LABEL_END)
    return m & pd.concat([(d >= a) & (d <= b) for a, b in SANDRP_SEASONS], axis=1).any(axis=1)


def near(a: pd.DataFrame, b: pd.DataFrame, tol=1) -> pd.Series:
    """For each row of a: is there a row of b in the same district within ±tol days?"""
    idx = {k: g["date"].to_numpy() for k, g in b.groupby("district")}
    return pd.Series([bool(len(idx.get(r.district, []))) and (abs((idx[r.district] - r.date.to_datetime64()) / pd.Timedelta(days=1)) <= tol).any()
                      for r in a.itertuples()], index=a.index)


def events(days: pd.DataFrame) -> int:
    """Count distinct events: same district, consecutive days (gap <= 1) are one event."""
    n = 0
    for _, g in days.sort_values("date").groupby("district"):
        n += int((g["date"].diff().dt.days.fillna(99) > 1).sum())
    return n


def split_of(d: pd.Timestamp) -> str:
    return "train" if d < pd.Timestamp(TRAIN_END_DATE) else ("validation" if d < pd.Timestamp(VAL_END_DATE) else "test")


def alerted(days: pd.DataFrame) -> pd.Series:
    """Hybrid tier >= ALERT at any station of the district on the day or the day before (val/test only)."""
    frames = []
    for name in ("validation", "test"):
        p = RESULTS_DIR / f"warning_levels/{name}_warning_levels.csv"
        if p.exists():
            frames.append(pd.read_csv(p, usecols=["district", "datetime", "tier"], parse_dates=["datetime"]))
    if not frames:
        return pd.Series([None] * len(days), index=days.index)
    w = pd.concat(frames)
    w = w[w["tier"].map(RANK) >= RANK["ALERT"]]
    hit = set(zip(w["district"], w["datetime"].dt.normalize()))
    covered = (days["date"] >= pd.Timestamp(TRAIN_END_DATE)) & (days["date"] <= LABEL_END)
    return pd.Series([(r.district, r.date) in hit or (r.district, r.date - pd.Timedelta(days=1)) in hit if c else None
                      for r, c in zip(days.itertuples(), covered)], index=days.index)


def run():
    d = pd.read_csv(LAB / "labels_daily.csv", parse_dates=["date"])
    d = d[in_overlap(d["date"])]
    imd = d[d["source"] == "imd"].drop_duplicates(["district", "date"]).copy()
    san = d[d["source"] == "sandrp"].drop_duplicates(["district", "date"]).copy()
    imd["in_sandrp"] = near(imd, san)
    san["in_imd"] = near(san, imd)
    only = san[~san["in_imd"]].copy()
    only["split"] = only["date"].map(split_of)
    only["hybrid_alerted"] = alerted(only)

    per = pd.DataFrame({"imd_days": imd.groupby("district").size(), "sandrp_days": san.groupby("district").size(),
                        "matched_imd_days": imd[imd["in_sandrp"]].groupby("district").size(),
                        "sandrp_only_days": only.groupby("district").size()}).fillna(0).astype(int)
    n_imd_ev, n_only_ev = events(imd), events(only)
    share = n_only_ev / max(n_imd_ev, 1)
    va = only[only["hybrid_alerted"].notna()]
    res = {
        "overlap_period": [f"{max(a, LABEL_START):%Y-%m-%d}..{min(b, LABEL_END):%Y-%m-%d}" for a, b in SANDRP_SEASONS],
        "imd_district_days": len(imd), "sandrp_district_days": len(san),
        "imd_events": n_imd_ev, "sandrp_events": events(san),
        "imd_days_confirmed_by_sandrp": int(imd["in_sandrp"].sum()),
        "imd_confirmation_rate": round(imd["in_sandrp"].mean(), 3) if len(imd) else None,
        "sandrp_only_days": len(only), "sandrp_only_events": n_only_ev,
        "sandrp_only_by_split": only["split"].value_counts().to_dict(),
        "sandrp_only_valtest_alerted_by_hybrid": f"{int(va['hybrid_alerted'].sum())}/{len(va)}",
        "gate": {"rule": f"sandrp_only_events >= {GATE_SHARE:.0%} of imd_events", "share": round(share, 3), "passed": share >= GATE_SHARE},
        "note": "SANDRP tracks cloudbursts / flash floods in the hills; IMD-only days are mostly heavy-rain floods and "
                "landslides it does not list, so a low confirmation rate does not mean IMD is wrong.",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "label_audit.json").write_text(json.dumps({"summary": res, "by_district": per.reset_index(names="district").to_dict("records")}, indent=2, default=str))
    only.assign(date=only["date"].dt.date).to_csv(OUT / "sandrp_only_days.csv", index=False)
    per.to_csv(OUT / "label_audit_by_district.csv")
    print(per.to_string()); print(json.dumps(res, indent=2, default=str))
    return res


if __name__ == "__main__":
    run()
