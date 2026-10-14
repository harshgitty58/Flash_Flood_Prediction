"""Measure latency per path (in-process API, no network) and write results/latency/benchmarks.csv.

  python scripts/bench_latency.py
Compares the old path vs the new algorithm where both exist:
  buildings      one 8.7 MB GeoJSON  vs  adaptive quadtree tiles for one view
  features       batch rolling recompute over 96 h  vs  O(1) StationState.update
  calibration    exact Venn-Abers isotonic refit  vs  lookup-table interpolation
"""
import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient  # noqa: E402

from backend.app import app  # noqa: E402
from src.conformal import venn_abers  # noqa: E402
from src.online_features import StationState  # noqa: E402


def timeit(fn, n=30):
    out = []
    for _ in range(n):
        t0 = time.perf_counter(); fn(); out.append((time.perf_counter() - t0) * 1000)
    out.sort()
    return {"p50_ms": round(statistics.median(out), 3), "p95_ms": round(out[int(0.95 * (len(out) - 1))], 3)}


def main():
    rows = []
    with TestClient(app) as c:
        rows.append({"path": "API startup (load model, calibration, data)", "variant": "new", "p50_ms": c.get("/health").json()["startup_ms"], "p95_ms": None})
        for p in ["/risk/snapshot", "/model/summary", "/metrics"]:
            rows.append({"path": f"GET {p}", "variant": "new", **timeit(lambda: c.get(p))})
            et = c.get(p).headers["etag"]
            rows.append({"path": f"GET {p} (cached, 304)", "variant": "new", **timeit(lambda: c.get(p, headers={"If-None-Match": et}))})
        big = ROOT / "results/impact/buildings.geojson"
        rows.append({"path": "buildings for one view", "variant": "old: full GeoJSON", "bytes": big.stat().st_size,
                     **timeit(lambda: json.loads(big.read_bytes()), n=5)})
        idx = c.get("/impact/tiles/index").json()["tiles"]
        t = max(idx, key=lambda t: t["n"])
        rows.append({"path": "buildings for one view", "variant": "new: densest quadtree tile", "bytes": t["bytes"],
                     **timeit(lambda: c.get(f"/impact/tiles/{t['z']}/{t['x']}/{t['y']}"))})
        st = c.get("/stations").json()[0]["station"]
        rows.append({"path": "POST /predict (1 station, 1 new hour)", "variant": "new",
                     **timeit(lambda: c.post("/predict", json={"station": st, "readings": [{"datetime": "2026-09-14 23:00", "rain_mm": 3}]}))})

    # features: batch recompute vs O(1)
    hist = pd.Series(np.random.default_rng(0).gamma(0.3, 4, 96))
    def batch():
        s = hist
        _ = [s.rolling(w, min_periods=1).sum().iloc[-1] for w in (3, 6, 12, 24, 48, 72)], s.rolling(24).max().iloc[-1]
        a = 0.0
        for v in s:
            a = a * 0.85 + v
    stt = StationState()
    for i, v in enumerate(hist):
        stt.update(pd.Timestamp("2025-08-01") + pd.Timedelta(hours=i), v)
    rows.append({"path": "features for 1 station-hour", "variant": "old: batch recompute (96 h)", **timeit(batch, 200)})
    rows.append({"path": "features for 1 station-hour", "variant": "new: O(1) incremental",
                 **timeit(lambda: stt.update(stt.last_time + pd.Timedelta(hours=1), 1.0), 200)})

    cal = pd.read_csv(ROOT / "results/conformal/calibration_scores.csv")
    s, y = cal["score"].to_numpy(), cal["y"].to_numpy()
    x = np.array([0.4])
    rows.append({"path": "calibrate 1 score", "variant": "old: exact Venn-Abers (2 isotonic fits)",
                 **timeit(lambda: venn_abers(s, y, x) if False else _exact(s, y, 0.4), 5)})
    grid = np.unique(np.quantile(s, np.linspace(0, 1, 400))); g0, g1 = venn_abers(s, y, grid)
    rows.append({"path": "calibrate 1 score", "variant": "new: lookup table (np.interp)",
                 **timeit(lambda: (np.interp(x, grid, g0), np.interp(x, grid, g1)), 500)})

    out = ROOT / "results/latency"; out.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(out / "benchmarks.csv", index=False)
    print(df.to_string(index=False))


def _exact(s, y, u):
    from sklearn.isotonic import IsotonicRegression
    xs = np.append(s, u)
    return [IsotonicRegression(out_of_bounds="clip").fit(xs, np.append(y, lab)).predict([u])[0] for lab in (0, 1)]


if __name__ == "__main__":
    main()
