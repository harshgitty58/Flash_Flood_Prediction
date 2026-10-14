"""
Model-Specific Preprocessing Pipelines for Phase 3.
Guarantees training-only fitting for imputers and scalers.
"""

import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from typing import Tuple, Any
from src.normalization import FeatureNormalizer

def _imputer() -> SimpleImputer:
    # pandas output keeps feature names so the normaliser can pick a method per feature
    return SimpleImputer(strategy="median", keep_empty_features=True).set_output(transform="pandas")


def get_logistic_preprocessor() -> Pipeline:
    """Logistic Regression: median imputation + parameterised normalisation (log/robust/z-score per feature)."""
    return Pipeline([("imputer", _imputer()), ("normalizer", FeatureNormalizer())])


def get_tree_preprocessor() -> Pipeline:
    """Tree models: same imputation + normalisation. Monotone transforms do not change tree splits, but one
    shared, saved parameter set keeps training and inference (backend /predict) identical for every model."""
    return Pipeline([("imputer", _imputer()), ("normalizer", FeatureNormalizer())])

def calculate_scale_pos_weight(y_train: pd.Series) -> float:
    """Calculates scale_pos_weight strictly from the training partition: negative_count / positive_count."""
    neg = int((y_train == 0).sum())
    pos = int((y_train == 1).sum())
    if pos == 0:
        return 1.0
    return round(float(neg / pos), 2)
