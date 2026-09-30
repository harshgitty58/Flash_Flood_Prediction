"""
Feature Selection and Ablation Module for Phase 3.
Implements correlation analysis, importance ranking, and feature ablation experiments on development data.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Any
from src.model_config import FEATURE_SELECT_DIR
from src.evaluate import compute_all_metrics

def find_collinear_features(X_train: pd.DataFrame, threshold: float = 0.95) -> Tuple[List[str], pd.DataFrame]:
    """Finds highly correlated feature pairs (|r| > threshold) on training data only."""
    FEATURE_SELECT_DIR.mkdir(parents=True, exist_ok=True)
    corr_matrix = X_train.corr().abs()
    upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    
    to_drop = [column for column in upper.columns if any(upper[column] > threshold)]
    
    # Save correlation report
    collinear_pairs = []
    for col in upper.columns:
        high_corr = upper[col][upper[col] > threshold]
        for idx, val in high_corr.items():
            collinear_pairs.append({
                "feature_1": idx,
                "feature_2": col,
                "correlation": round(float(val), 4),
            })
            
    corr_df = pd.DataFrame(collinear_pairs)
    corr_df.to_csv(FEATURE_SELECT_DIR / "collinear_features.csv", index=False)
    return to_drop, corr_df

def extract_feature_importance(model: Any, feature_names: List[str], model_name: str) -> pd.DataFrame:
    """Extracts standardized feature importances or coefficients from a fitted model pipeline."""
    FEATURE_SELECT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get the inner classifier
    classifier = model.named_steps.get("classifier", model)
    
    if hasattr(classifier, "feature_importances_"):
        importances = classifier.feature_importances_
        metric_name = "gini_gain_importance"
    elif hasattr(classifier, "coef_"):
        importances = np.abs(classifier.coef_[0])
        metric_name = "abs_coefficient"
    else:
        importances = np.ones(len(feature_names))
        metric_name = "uniform"
        
    # Ensure length match safely
    names = feature_names if len(importances) == len(feature_names) else [f"feat_{i}" for i in range(len(importances))]
    
    df = pd.DataFrame({
        "feature": names,
        "importance": importances,
        "metric": metric_name,
        "model": model_name,
    }).sort_values(by="importance", ascending=False).reset_index(drop=True)
    
    clean_name = model_name.lower().replace(" ", "_")
    df.to_csv(FEATURE_SELECT_DIR / f"{clean_name}_importance.csv", index=False)
    return df
