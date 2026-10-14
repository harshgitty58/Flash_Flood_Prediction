"""Execute notebooks 09-14 headless, in order, one batch at a time; outputs are saved into each .ipynb.
Stops at the first failing batch and records timings in results/notebook_runs.csv.

  python scripts/run_notebooks.py            # all batches
  python scripts/run_notebooks.py --from 12  # resume
"""
import argparse
import time
from datetime import datetime
from pathlib import Path

import nbformat
import pandas as pd
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
BATCHES = ["09_data_window_and_normalization", "10_retrain_models", "11_event_validation",
           "12_uncertainty_calibration", "13_warning_levels_hybrid", "14_explainability_robustness_metrics",
           "15_labels_and_model_upgrades"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", default="09")
    ap.add_argument("--only", default=None)
    a = ap.parse_args()
    todo = [b for b in BATCHES if b[:2] >= a.start and (a.only is None or b.startswith(a.only))]
    log = []
    for b in todo:
        path = ROOT / "notebooks" / f"{b}.ipynb"
        nb = nbformat.read(path, as_version=4)
        t0 = time.time()
        print(f"[batch {b}] running…", flush=True)
        status = "ok"
        try:
            NotebookClient(nb, timeout=3600, kernel_name="prahar", resources={"metadata": {"path": str(ROOT / "notebooks")}}).execute()
        except Exception as e:  # keep partial outputs for debugging
            status = f"FAILED: {type(e).__name__}: {str(e).splitlines()[-1][:300] if str(e) else ''}"
        nbformat.write(nb, path)
        dt = round(time.time() - t0, 1)
        log.append({"batch": b, "status": status, "seconds": dt, "finished": datetime.now().isoformat(timespec="seconds")})
        print(f"[batch {b}] {status} in {dt}s", flush=True)
        if status != "ok":
            break
    f = ROOT / "results" / "notebook_runs.csv"
    pd.concat([pd.read_csv(f), pd.DataFrame(log)]) .to_csv(f, index=False) if f.exists() else pd.DataFrame(log).to_csv(f, index=False)
    raise SystemExit(0 if all(r["status"] == "ok" for r in log) else 1)


if __name__ == "__main__":
    main()
