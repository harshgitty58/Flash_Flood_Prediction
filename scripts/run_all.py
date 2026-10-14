"""Run the whole PRAHAR chain in dependency order, then audit it.

  python scripts/run_all.py              # everything
  python scripts/run_all.py --from conformal   # resume from a stage

Stages: data → labels → train → event_cv → conformal → warning → label_audit → label_exp → external → verification → shap → robustness → metrics → report → export → impact
        → tiles → tests → bench → apis → audit   (notebooks 09-14 run the same modules: scripts/run_notebooks.py)
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = [sys.executable, "-u", "-W", "ignore"]
STAGES = [
    ("data", PY + ["-m", "src.pipeline"]),
    ("labels", PY + ["scripts/build_labels.py"]),
    ("train", PY + ["-m", "src.train_pipeline"]),
    ("norm", PY + ["scripts/export_normalization.py"]),
    ("event_cv", PY + ["-m", "src.event_cv"]),
    ("conformal", PY + ["-m", "src.conformal"]),
    ("warning", PY + ["-m", "src.warning_levels"]),
    ("label_audit", PY + ["-m", "src.label_audit"]),
    ("label_exp", PY + ["-m", "src.label_experiment"]),
    ("external", PY + ["-m", "src.external_validation"]),
    ("district_day", PY + ["-m", "src.district_day"]),
    ("e1_ensemble", PY + ["-m", "src.ensemble"]),
    ("e2_thresholds", PY + ["-m", "src.rain_thresholds"]),
    ("e3_pooled", PY + ["-m", "src.district_pooled"]),
    ("upgrade_report", PY + ["scripts/model_upgrade_report.py"]),
    ("verification", PY + ["-m", "src.verification"]),
    ("shap", PY + ["-m", "src.explain"]),
    ("robustness", PY + ["-m", "src.robustness"]),
    ("metrics", PY + ["-m", "src.metrics_report"]),
    ("report", PY + ["-m", "src.phase4_report"]),
    ("label_report", PY + ["scripts/label_impact_report.py"]),
    ("export", PY + ["scripts/export_frontend_data.py"]),
    ("impact", PY + ["scripts/build_impact_layer.py"]),
    ("tiles", PY + ["scripts/build_building_tiles.py"]),
    ("tests", PY + ["-m", "pytest", "-q", "-m", "not network", "tests"]),
    ("bench", PY + ["scripts/bench_latency.py"]),
    ("apis", PY + ["scripts/check_apis.py"]),
    ("audit", PY + ["scripts/audit_pipeline.py"]),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", default="data", choices=[s for s, _ in STAGES])
    names = [s for s, _ in STAGES]
    for name, cmd in STAGES[names.index(ap.parse_args().start):]:
        t0 = time.time()
        print(f"\n===== {name} =====", flush=True)
        r = subprocess.run(cmd, cwd=ROOT, env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
        print(f"===== {name}: exit {r.returncode} in {time.time() - t0:.0f}s =====", flush=True)
        if r.returncode != 0:
            sys.exit(r.returncode)


if __name__ == "__main__":
    main()
