"""Generate the Phase D/M notebooks (09-15). Each is a thin, readable driver over src/ modules.
Run: python scripts/make_notebooks.py [name ...]   (no names = all; regenerating clears outputs)   then   python scripts/run_notebooks.py
"""
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks"

SETUP = """import os, sys, json, subprocess
from pathlib import Path
ROOT = Path.cwd() if (Path.cwd() / "src").exists() else Path.cwd().parent
os.chdir(ROOT); sys.path.insert(0, str(ROOT))
import pandas as pd
from IPython.display import Image, Markdown, display
pd.set_option("display.width", 200); pd.set_option("display.max_columns", 30)"""

NOTEBOOKS = {
    "09_data_window_and_normalization": [
        ("md", "# 09 · Data window, quality and normalisation (Phase D)\nRebuild the dataset from the raw CWC/IMD/GSI files, "
               "verify every data contract, pick the study window where sources meet, and fit normalisation parameters on the training split only."),
        ("code", SETUP),
        ("md", "## 1. Rebuild cleaned → hourly → final table"),
        ("code", "from src.pipeline import run_objective_2_pipeline\nbase = run_objective_2_pipeline()\nbase.shape"),
        ("md", "## 2. Coverage: where do the datasets meet?"),
        ("code", "from src.data_window import run as coverage_run\ncov, windows = coverage_run()\ndisplay(Image(filename='results/data_audit/coverage_heatmap.png'))\npd.DataFrame(windows).T"),
        ("md", "## 3. Data contract tests"),
        ("code", "r = subprocess.run([sys.executable, '-m', 'pytest', '-q', 'tests/test_data.py'], capture_output=True, text=True)\nprint(r.stdout[-2000:]); assert r.returncode == 0, 'data tests failed'"),
        ("md", "## 4. Train / validation / test partition (recorded once in results/splits.json)"),
        ("code", "from src.data_loader import load_ml_dataset\nfrom src.split import get_chronological_splits\ntrain_df, val_df, test_df = get_chronological_splits(load_ml_dataset())\npd.DataFrame(json.loads(Path('results/splits.json').read_text())).T"),
        ("md", "## 5. Normalisation parameters (fitted on the training split only)"),
        ("code", "from src.data_loader import FEATURE_EXPERIMENTS, FINAL_EXPERIMENT\nfrom src.preprocessing import get_tree_preprocessor\n"
                 "feats = FEATURE_EXPERIMENTS[FINAL_EXPERIMENT]\npre = get_tree_preprocessor().fit(train_df[feats])\n"
                 "s = json.loads(Path('results/splits.json').read_text())['train']\n"
                 "pre['normalizer'].to_json(Path('results/preprocessing/normalization_params.json'), fit_window={'start': s['start'], 'end': s['end']})\n"
                 "pd.DataFrame(pre['normalizer'].params_).round(4)"),
    ],
    "10_retrain_models": [
        ("md", "# 10 · Retrain LR / RF / XGBoost on Window A (Phase M2)\nTime-series CV tuning on train, threshold frozen on validation, single pass on test."),
        ("code", SETUP),
        ("code", "from src.train_pipeline import run_phase_3_pipeline\nrun_phase_3_pipeline()"),
        ("code", "pd.read_csv('results/model_evaluation/model_comparison.csv')"),
        ("code", "pd.read_csv('results/feature_selection/feature_fusion_experiments.csv').query(\"model == 'XGBoost'\")"),
    ],
    "11_event_validation": [
        ("md", "# 11 · Leave-one-event-out validation and lead time (Phase M3)\nEach flood episode is held out in turn; this is the primary skill estimate."),
        ("code", SETUP),
        ("code", "from src.event_cv import run, lead_times\nsummary = run()\nsummary"),
        ("code", "lt = lead_times()\nlt"),
    ],
    "12_uncertainty_calibration": [
        ("md", "# 12 · Calibration and conformal uncertainty (Phase M4)"),
        ("code", SETUP),
        ("code", "from src.conformal import calibrate\nsummary = calibrate()\npd.DataFrame(summary['coverage'])"),
    ],
    "13_warning_levels_hybrid": [
        ("md", "# 13 · Hybrid warning tiers (Phase M5)\nFinal tier = max(ML tier, IMD-rainfall tier adjusted for susceptibility)."),
        ("code", SETUP),
        ("code", "from src.warning_levels import run\nrun()\npd.DataFrame(json.loads(Path('results/warning_levels/warning_thresholds.json').read_text())['alert_level']).T"),
        ("md", "## Sanity check on documented disasters (unlabelled period)"),
        ("code", "r = pd.read_csv('results/warning_levels/replay_warning_levels.csv', parse_dates=['datetime'])\n"
                 "cases = {'Kedarnath route cloudburst': ('2024-07-31', ['Rudraprayag', 'Chamoli', 'Tehri Garhwal']),\n"
                 "         'Dharali / Uttarkashi': ('2025-08-05', ['Uttarkashi', 'Chamoli', 'Rudraprayag'])}\n"
                 "for name, (day, dists) in cases.items():\n"
                 "    d = pd.Timestamp(day)\n"
                 "    w = r[(r.datetime >= d - pd.Timedelta(days=1)) & (r.datetime < d + pd.Timedelta(days=1)) & r.district.isin(dists)]\n"
                 "    display(Markdown(f'**{name}** ({day})'))\n"
                 "    display(w.groupby('station').agg(max_tier=('tier', lambda x: max(x, key=['NORMAL','WATCH','ALERT','SEVERE','EXTREME'].index)),\n"
                 "                                     trigger=('trigger', lambda x: x.value_counts().index[0]), max_p=('p_calibrated', 'max')))"),
        ("md", "## External validation: curated 2024-2025 disasters (independent of training labels)"),
        ("code", "from src.external_validation import run as ext_run\next_run()"),
    ],
    "14_explainability_robustness_metrics": [
        ("md", "# 14 · SHAP, robustness and the consolidated metrics table (Phase M6)"),
        ("code", SETUP),
        ("code", "from src.explain import run as shap_run\nshap_run()\ndisplay(Image(filename='results/shap/shap_bar_chart.png'))"),
        ("code", "from src.robustness import run as rob_run\nrob_run()\ndisplay(Image(filename='results/robustness/robustness_curves.png'))"),
        ("md", "## Industry-standard verification: POD · FAR · CSI · ETS · HSS (station-hour and district-day), BSS, reliability, honest lead time"),
        ("code", "from src.verification import run as ver_run\nv = ver_run()\npd.DataFrame(v['contingency']).query(\"split == 'test' and level == '≥ ALERT'\")[['unit','layer','events','POD','FAR','CSI','ETS','HSS','bias']]"),
        ("md", "## Precision · recall · F1 · MCC · ROC-AUC · PR-AUC (hour level, frozen thresholds)"),
        ("code", "from src.metrics_report import run as metrics_run\nm = metrics_run()\npd.read_csv('results/metrics/metrics_summary.csv')"),
        ("code", "from src.phase4_report import run as report_run\nreport_run()\ndisplay(Markdown(Path('results/phase4_report.md').read_text(encoding='utf-8')[:6000]))"),
    ],    "15_labels_and_model_upgrades": [
        ("md", "# 15 · Ground truth and model upgrades (LABELS_PLAN.md, MODEL_UPGRADE_PLAN.md)\nEvery adoption rule is written in the module docstring before the run."),
        ("code", SETUP),
        ("md", "## 1. Multi-source label set (IMD + SANDRP + Sphere India SitReps + EM-DAT + curated news)"),
        ("code", "print(subprocess.run([sys.executable, 'scripts/build_labels.py'], capture_output=True, text=True).stdout)\npd.read_csv('data/external/labels/labels_2022_2025.csv').head(20)"),
        ("md", "## 2. Audit: IMD vs SANDRP on the overlap period"),
        ("code", "from src.label_audit import run as audit_run\naudit_run();"),
        ("md", "## 3. Label v1 vs v2 (2×2 train-label × truth grid; slow, so results are read from the last run of src.label_experiment)"),
        ("code", "e = json.loads(Path('results/labels/label_experiment.json').read_text())\ndisplay(pd.DataFrame(e['grid']).query(\"model == 'XGBoost'\"))\ne['decision']"),
        ("md", "## 4. District-day model (CWC + USDMA hydromet + ERA5)"),
        ("code", "from src.district_day import run as dd_run\ndd = dd_run()\ndd['decision']"),
        ("md", "## 5. E1 ensemble · E2 event-fitted rain thresholds · E3 pooled district-day + ranking"),
        ("code", "from src.ensemble import run as e1\nfrom src.rain_thresholds import run as e2\nfrom src.district_pooled import run as e3\nr1, r2, r3 = e1(), e2(), e3()"),
        ("code", "print(subprocess.run([sys.executable, 'scripts/model_upgrade_report.py'], capture_output=True, text=True).stdout[:200])\ndisplay(Markdown(Path('results/model_upgrade.md').read_text(encoding='utf-8')))"),
    ],
}


def main():
    import sys
    for name, cells in ((n, NOTEBOOKS[n]) for n in (sys.argv[1:] or NOTEBOOKS)):
        nb = nbf.v4.new_notebook()
        nb.metadata["kernelspec"] = {"name": "prahar", "display_name": "PRAHAR (py3.13)", "language": "python"}
        nb.cells = [nbf.v4.new_markdown_cell(c) if k == "md" else nbf.v4.new_code_cell(c) for k, c in cells]
        nbf.write(nb, NB / f"{name}.ipynb")
        print("wrote", f"notebooks/{name}.ipynb")


if __name__ == "__main__":
    main()
