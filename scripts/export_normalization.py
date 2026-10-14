"""Write results/preprocessing/normalization_params.json (fitted on the training split only) — same code as notebook 10,
so the full chain (scripts/run_all.py) keeps it in step with the final dataset. Run: python scripts/export_normalization.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data_loader import FEATURE_EXPERIMENTS, FINAL_EXPERIMENT, load_ml_dataset  # noqa: E402
from src.preprocessing import get_tree_preprocessor  # noqa: E402
from src.split import get_chronological_splits  # noqa: E402

train_df, _, _ = get_chronological_splits(load_ml_dataset())
feats = FEATURE_EXPERIMENTS[FINAL_EXPERIMENT]
pre = get_tree_preprocessor().fit(train_df[feats])
s = json.loads((ROOT / "results/splits.json").read_text())["train"]
pre["normalizer"].to_json(ROOT / "results/preprocessing/normalization_params.json", fit_window={"start": s["start"], "end": s["end"]})
print(f"normalization params for {len(feats)} features written")
