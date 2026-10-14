"""Check every external service + the local API, and write web/public/data/system.json for the System page.

  python scripts/check_apis.py            (local API checked only if it is running on :8000)
"""
import json
import sys
import time
from pathlib import Path

import httpx
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app import EXTERNAL  # noqa: E402

LOCAL = ["/health", "/risk/snapshot", "/metrics", "/impact/tiles/index"]


def probe(client, name, url, method="GET"):
    t0 = time.perf_counter()
    try:
        r = client.request(method, url, headers={"User-Agent": "PRAHAR-health/1.0", "Range": "bytes=0-2047"})
        return {"name": name, "ok": r.status_code < 400, "status": r.status_code, "ms": round((time.perf_counter() - t0) * 1000)}
    except Exception as e:  # noqa: BLE001
        return {"name": name, "ok": False, "status": None, "ms": round((time.perf_counter() - t0) * 1000), "error": type(e).__name__}


def main():
    with httpx.Client(timeout=10, follow_redirects=True) as c:
        ext = [probe(c, n, u) for n, u in EXTERNAL.items()]
        local = [probe(c, p, f"http://127.0.0.1:8000{p}") for p in LOCAL]
    api_up = any(r["ok"] for r in local)
    bench = ROOT / "results/latency/benchmarks.csv"
    runs = ROOT / "results/notebook_runs.csv"
    out = {"checked_at": pd.Timestamp.now().isoformat(timespec="seconds"),
           "external": ext, "local_api": local if api_up else [], "local_api_running": api_up,
           "latency": pd.read_csv(bench).astype(object).where(pd.read_csv(bench).notna(), None).to_dict("records") if bench.exists() else [],
           "notebook_runs": pd.read_csv(runs).drop_duplicates("batch", keep="last").sort_values("batch").to_dict("records") if runs.exists() else []}
    (ROOT / "web/public/data/system.json").write_text(json.dumps(out, indent=1, default=str))
    for r in ext + local:
        print(f"{'OK  ' if r['ok'] else 'DOWN'} {r['ms']:>5} ms  {r['name']}  {r.get('status') or r.get('error')}")
    print(f"external {sum(r['ok'] for r in ext)}/{len(ext)} up; local API {'running' if api_up else 'not running'}")


if __name__ == "__main__":
    main()
