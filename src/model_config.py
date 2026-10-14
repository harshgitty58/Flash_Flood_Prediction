"""
Configuration and Directory Management for Phase 3 (Objective 3).
Defines paths, metrics, seeds, and hyperparameter search grids.
"""

from pathlib import Path
from src.config import PROJECT_ROOT, FINAL_PARQUET_FILE, FINAL_CSV_FILE

# Output Directories for Phase 3
MODELS_DIR = PROJECT_ROOT / "models"
LOGISTIC_MODEL_DIR = MODELS_DIR / "logistic_regression"
RF_MODEL_DIR = MODELS_DIR / "random_forest"
XGB_MODEL_DIR = MODELS_DIR / "xgboost"

RESULTS_DIR = PROJECT_ROOT / "results"
EVALUATION_DIR = RESULTS_DIR / "model_evaluation"
TUNING_DIR = RESULTS_DIR / "hyperparameter_tuning"
PREDICTIONS_DIR = RESULTS_DIR / "predictions"
FEATURE_SELECT_DIR = RESULTS_DIR / "feature_selection"
PLOTS_DIR = RESULTS_DIR / "plots"

# Random Seed for Reproducibility
RANDOM_STATE = 42

# Target Variable
TARGET_COL = "flood_event_24h"

# Date Thresholds for Chronological Splitting
# Train: < 2023-01-01 (Earlier period covering 2022 monsoon events)
# Validation: 2023-01-01 to 2023-08-01 (Covering July 2023 peak monsoon events)
# Test: >= 2023-08-01 (Covering August 2023 events and forward through 2026)
TRAIN_END_DATE = "2023-07-01"  # train: 2022 monsoon + H1 2023 (2022 alone has only 19 stations)
VAL_END_DATE = "2023-08-01"

# Evaluation Metrics List
METRICS = [
    "roc_auc",
    "pr_auc",
    "precision",
    "recall",
    "f1",
    "specificity",
    "balanced_accuracy",
    "mcc",
    "brier",
    "log_loss",
]

def ensure_phase3_directories():
    """Ensures all Phase 3 required directories exist."""
    for d in [
        MODELS_DIR,
        LOGISTIC_MODEL_DIR,
        RF_MODEL_DIR,
        XGB_MODEL_DIR,
        EVALUATION_DIR,
        TUNING_DIR,
        PREDICTIONS_DIR,
        FEATURE_SELECT_DIR,
        PLOTS_DIR,
    ]:
        d.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    ensure_phase3_directories()
    print("Phase 3 directories initialized.")
