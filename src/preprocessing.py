"""
Model-Specific Preprocessing Pipelines for Phase 3.
Guarantees training-only fitting for imputers and scalers.
"""

import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from typing import Tuple, Any

def get_logistic_preprocessor() -> Pipeline:
    """Constructs preprocessing pipeline for Logistic Regression: Median Imputation + StandardScaler."""
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
        ("scaler", StandardScaler()),
    ])

def get_tree_preprocessor() -> Pipeline:
    """Constructs preprocessing pipeline for Tree models (RF, XGBoost): Median Imputation."""
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
    ])

def calculate_scale_pos_weight(y_train: pd.Series) -> float:
    """Calculates scale_pos_weight strictly from the training partition: negative_count / positive_count."""
    neg = int((y_train == 0).sum())
    pos = int((y_train == 1).sum())
    if pos == 0:
        return 1.0
    return round(float(neg / pos), 2)
