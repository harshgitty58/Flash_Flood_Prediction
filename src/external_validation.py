"""
External validation on documented events after the training labels end (D2; LABELS_PLAN.md §6).

Events come from data/external/labels/labels_2022_2025.csv (scripts/build_labels.py: SANDRP, Sphere India SitReps,
EM-DAT, curated news list), restricted to dates after the IMD inventory's coverage end, so none of them was seen in
training. The lists cover major, reported disasters only, so "no report" cannot be read as "no flood": they are an
independent test of detection (POD), never training labels, and a true FAR cannot be computed.

Per event: did any reporting station in the district reach >= ALERT / >= SEVERE (hybrid, ML-only, rainfall-only)
between the day before the event and its last day; when was the first such warning.
Summary: POD with a bootstrap CI over events, split by date confidence and severity, plus the alert burden
(ALERT+ district-days per monsoon, and the share within ±2 days of a documented event) as a false-alarm proxy.
Run: python -m src.external_validation   (after src.warning_levels and scripts/build_labels.py)
"""
import json

import numpy as np
import pandas as pd

from src.config import CLEANED_DIR, PROJECT_ROOT
from src.model_config import RANDOM_STATE, RESULTS_DIR

RANK = {"NORMAL": 0, "WATCH": 1, "ALERT": 2, "SEVERE": 3, "EXTREME": 4}
SRC = PROJECT_ROOT / "data/external/labels/labels_2022_2025.csv"


def _events() -> pd.DataFrame:
    ev = pd.read_csv(SRC, parse_dates=["date", "end_date"])
    end = pd.read_parquet(CLEANED_DIR / "flood_inventory_cleaned.parquet")["start_datetime"].max()
    return ev[ev["date"] > end].reset_index(drop=True)


def _pod_ci(hits: np.ndarray, n=2000) -> list:
    if len(hits) == 0:
        return [None, None]
    rng = np.random.default_rng(RANDOM_STATE)
    b = rng.choice(hits, (n, len(hits)), replace=True).mean(axis=1)
    return [round(float(np.percentile(b, 2.5)), 3), round(float(np.percentile(b, 97.5)), 3)]


def alert_burden(r: pd.DataFrame, ev: pd.DataFrame) -> list[dict]:
    """ALERT+ district-days per monsoon (Jun-Sep) and the share within ±2 days of a documented event."""
    a = r[r["tier_rank"] >= RANK["ALERT"]].assign(day=r["datetime"].dt.normalize())[["district", "day"]].drop_duplicates()
    a = a[a["day"].dt.month.between(6, 9)]
    near = set()
    for _, e in ev.iterrows():
        for d in pd.date_range(e["date"] - pd.Timedelta(days=2), e["end_date"] + pd.Timedelta(days=2)):
            near.add((e["district"], d))
    a["near_event"] = [(x, d) in near for x, d in zip(a["district"], a["day"])]
    out = []
    for y, g in a.groupby(a["day"].dt.year):
        out.append({"monsoon": int(y), "alert_district_days": len(g), "near_documented_event": int(g["near_event"].sum()),
                    "share_near_event": round(float(g["near_event"].mean()), 3)})
    return out


def run():
    ev = _events()
    r = pd.read_csv(RESULTS_DIR / "warning_levels/replay_warning_levels.csv", parse_dates=["datetime"],
                    usecols=["station", "district", "datetime", "p_calibrated", "tier", "tier_ml", "tier_rain", "trigger"])
    for c in ("tier", "tier_ml", "tier_rain"):
        r[c + "_rank"] = r[c].map(RANK)
    rows = []
    for _, e in ev.iterrows():
        start, end = e["date"] - pd.Timedelta(days=1), e["end_date"] + pd.Timedelta(days=1)
        w = r[(r["district"] == e["district"]) & (r["datetime"] >= start) & (r["datetime"] < end)]
        row = {"event_id": e["event_id"], "date": e["date"].date(), "end_date": e["end_date"].date(), "district": e["district"],
               "place": e["place"] if isinstance(e["place"], str) else None, "type": e["type"], "severity": e["severity"],
               "date_confidence": e["date_confidence"], "sources": e["sources"], "stations_reporting": int(w["station"].nunique())}
        for name, col in (("hybrid", "tier_rank"), ("ml", "tier_ml_rank"), ("rain", "tier_rain_rank")):
            for lvl, k in (("alert", 2), ("severe", 3)):
                hit = w[w[col] >= k]
                row[f"{name}_{lvl}"] = bool(len(hit)) if len(w) else None
                if name == "hybrid" and lvl == "alert":
                    row["first_alert"] = str(hit["datetime"].min()) if len(hit) else None
                    row["lead_h_to_day_end"] = round((e["date"] + pd.Timedelta(days=1) - hit["datetime"].min()).total_seconds() / 3600, 1) if len(hit) else None
        row["max_tier"] = max(w["tier"], key=RANK.get) if len(w) else "NO DATA"
        row["trigger_at_max"] = w.loc[w["tier_rank"].idxmax(), "trigger"] if len(w) else None
        refs = str(e["source_ref"]).split(" | ")
        row["source_url"] = next((s for s in refs if s.startswith("http")), refs[0])
        rows.append(row)
    res = pd.DataFrame(rows)
    res.to_csv(RESULTS_DIR / "metrics/external_validation.csv", index=False)

    cov = res[res["stations_reporting"] > 0]
    pod = lambda g, c="hybrid_alert": {"n": int(len(g)), "detected": int(g[c].sum()), "POD": round(float(g[c].mean()), 3) if len(g) else None,  # noqa: E731
                                       "ci95": _pod_ci(g[c].astype(float).to_numpy())}
    summ = {"events": int(len(res)), "events_with_station_data": int(len(cov)),
            **{f"{n}_{l}_detected": int(cov[f"{n}_{l}"].sum()) for n in ("hybrid", "ml", "rain") for l in ("alert", "severe")},
            "pod_hybrid_alert": pod(cov), "pod_ml_alert": pod(cov, "ml_alert"), "pod_rain_alert": pod(cov, "rain_alert"),
            "by_confidence": {k: pod(g) for k, g in cov.groupby("date_confidence")},
            "by_severity": {k: pod(g) for k, g in cov.groupby("severity")},
            "alert_burden": alert_burden(r, ev),
            "period": f"{ev['date'].min():%Y-%m-%d}..{ev['end_date'].max():%Y-%m-%d}",
            "source_file": SRC.relative_to(PROJECT_ROOT).as_posix(),
            "note": "Documented-disaster lists are incomplete, so FAR is not computable; alert_burden is the proxy."}
    out = {"summary": summ, "events": res.astype(object).where(res.notna(), None).to_dict("records")}
    (RESULTS_DIR / "metrics/external_validation.json").write_text(json.dumps(out, indent=2, default=str))
    print(res[["event_id", "district", "date_confidence", "severity", "stations_reporting", "hybrid_alert", "ml_alert", "rain_alert", "max_tier"]].to_string(index=False))
    print(json.dumps({k: v for k, v in summ.items() if k != "alert_burden"}, indent=1, default=str)); print(summ["alert_burden"])
    return res


if __name__ == "__main__":
    run()
