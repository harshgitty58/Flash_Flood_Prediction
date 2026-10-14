"""
D1 — Source coverage and the study window.

Builds a source × month coverage matrix (rainfall stations reporting, discharge gauges reporting, recorded flood
events) and records the window used for training (Window A: where rainfall and labels meet).
Run: python -m src.data_window
"""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from src.config import AUDIT_DIR, CLEANED_DIR, RESULTS_DIR  # noqa: E402

STUDY_START = pd.Timestamp("2022-02-01")  # first month with valid rainfall (2022-01-31)


def coverage() -> pd.DataFrame:
    rain = pd.read_parquet(CLEANED_DIR / "rainfall_cleaned.parquet")
    rain = rain[rain["rainfall_quality_flag"] == "valid"]
    dis = pd.read_parquet(CLEANED_DIR / "discharge_cleaned.parquet")
    dcol = next(c for c in dis.columns if "discharge" in c and "clean" in c)
    dis = dis[dis[dcol].notna()]
    inv = pd.read_parquet(CLEANED_DIR / "flood_inventory_cleaned.parquet")
    inv = inv[inv["start_datetime"] >= "2021-01-01"]
    m = lambda s: s.dt.to_period("M")  # noqa: E731
    cov = pd.DataFrame({
        "rain_stations": rain.groupby(m(rain["datetime"]))["station"].nunique(),
        "discharge_gauges": dis.groupby(m(dis["datetime"]))["station"].nunique(),
        "flood_events": inv.groupby(m(inv["start_datetime"])).size(),
    }).fillna(0).astype(int)
    cov.index = cov.index.astype(str)
    return cov.sort_index()


def run():
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    cov = coverage()
    cov.to_csv(AUDIT_DIR / "coverage_matrix.csv")
    inv = pd.read_parquet(CLEANED_DIR / "flood_inventory_cleaned.parquet")
    label_end = inv["start_datetime"].max().normalize()
    windows = {
        "A_train_window": {"start": str(STUDY_START.date()), "end": str((label_end - pd.Timedelta(days=1)).date()),
                           "sources": "rainfall + labels (+ discharge where present)", "used_for": "training / validation / test"},
        "B_all_sources": {"start": "2023-06-07", "end": str((label_end - pd.Timedelta(days=1)).date()),
                          "sources": "rainfall + discharge + labels", "used_for": "reported only (too short to train)"},
        "C_sensor_overlap": {"start": "2023-06-07", "end": "2025-12-31",
                             "sources": "rainfall + discharge (labels need curation)", "used_for": "replay now; training after label curation"},
        "replay": {"start": str(label_end.date()), "end": None, "used_for": "inference / replay only (unlabelled)"},
    }
    (RESULTS_DIR / "data_windows.json").write_text(json.dumps(windows, indent=2))

    fig, ax = plt.subplots(figsize=(13, 3.2))
    norm = cov / cov.max()
    ax.imshow(norm.T.values, aspect="auto", cmap="Greens")
    ax.set_yticks(range(3), ["Rain stations", "Discharge gauges", "Flood events"])
    ticks = [i for i, p in enumerate(cov.index) if p.endswith("-01") or p.endswith("-07")]
    ax.set_xticks(ticks, [cov.index[i] for i in ticks], rotation=45, fontsize=8)
    for name, w, col in [("A", windows["A_train_window"], "#ff9f1c"), ("C", windows["C_sensor_overlap"], "#4fb3f0")]:
        idx = [i for i, p in enumerate(cov.index) if w["start"][:7] <= p <= (w["end"] or "9999")[:7]]
        if idx:
            ax.axvspan(idx[0] - .5, idx[-1] + .5, fill=False, edgecolor=col, lw=2, label=f"Window {name}")
    ax.legend(loc="upper left", fontsize=8)
    ax.set_title("Data coverage by month (darker = more stations / events)")
    fig.tight_layout()
    fig.savefig(AUDIT_DIR / "coverage_heatmap.png", dpi=150)
    print(cov.to_string()); print(json.dumps(windows, indent=1))
    return cov, windows


if __name__ == "__main__":
    run()
