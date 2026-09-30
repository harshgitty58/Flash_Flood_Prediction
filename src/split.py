"""
Chronological Splitting and Time-Aware Validation Module for Phase 3.
Guarantees zero future leakage by enforcing strictly temporal partitions.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any, List
from src.model_config import TRAIN_END_DATE, VAL_END_DATE, TARGET_COL

def get_chronological_splits(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Splits dataset chronologically into Train, Validation, and Holdout Test."""
    dt = pd.to_datetime(df["datetime"])
    
    train_mask = dt < pd.to_datetime(TRAIN_END_DATE)
    val_mask = (dt >= pd.to_datetime(TRAIN_END_DATE)) & (dt < pd.to_datetime(VAL_END_DATE))
    test_mask = dt >= pd.to_datetime(VAL_END_DATE)
    
    # If the train or val has 0 positives due to rigid date cutoffs, adjust slightly to ensure development representation
    # Check positive counts
    y_train = df.loc[train_mask, TARGET_COL]
    y_val = df.loc[val_mask, TARGET_COL]
    y_test = df.loc[test_mask, TARGET_COL]
    
    # If train or val is empty or has 0 positives, fall back to quantiles of unique sorted timestamps
    if y_train.sum() == 0 or y_val.sum() == 0 or len(y_val) == 0:
        sorted_times = np.sort(df["datetime"].unique())
        idx_train = int(len(sorted_times) * 0.50)
        idx_val = int(len(sorted_times) * 0.70)
        
        t_split1 = sorted_times[idx_train]
        t_split2 = sorted_times[idx_val]
        
        train_mask = dt < t_split1
        val_mask = (dt >= t_split1) & (dt < t_split2)
        test_mask = dt >= t_split2
        
    train_df = df[train_mask].copy().reset_index(drop=True)
    val_df = df[val_mask].copy().reset_index(drop=True)
    test_df = df[test_mask].copy().reset_index(drop=True)
    
    return train_df, val_df, test_df

def compute_rare_event_stats(df: pd.DataFrame, split_name: str) -> Dict[str, Any]:
    """Computes class distribution and positive event rate for a split."""
    total = len(df)
    positives = int((df[TARGET_COL] == 1).sum())
    negatives = int((df[TARGET_COL] == 0).sum())
    pos_rate = round((positives / total) * 100, 3) if total > 0 else 0.0
    
    return {
        "split": split_name,
        "total_records": total,
        "flood_positives": positives,
        "flood_negatives": negatives,
        "positive_rate_pct": pos_rate,
        "date_start": str(df["datetime"].min())[:10] if total > 0 else "N/A",
        "date_end": str(df["datetime"].max())[:10] if total > 0 else "N/A",
    }

def get_time_series_cv_splits(train_df: pd.DataFrame, n_splits: int = 3) -> List[Tuple[np.ndarray, np.ndarray]]:
    """Generates expanding-window chronological cross-validation folds on the training set."""
    # Sort chronologically
    sorted_df = train_df.sort_values("datetime").reset_index(drop=True)
    unique_times = np.sort(sorted_df["datetime"].unique())
    n_times = len(unique_times)
    
    cv_folds = []
    # Divide time into n_splits + 1 slices
    step = n_times // (n_splits + 1)
    
    for i in range(1, n_splits + 1):
        train_times = unique_times[: step * i]
        val_times = unique_times[step * i : step * (i + 1)]
        
        train_idx = sorted_df[sorted_df["datetime"].isin(train_times)].index.values
        val_idx = sorted_df[sorted_df["datetime"].isin(val_times)].index.values
        
        # Ensure validation fold has at least some data
        if len(train_idx) > 0 and len(val_idx) > 0:
            cv_folds.append((train_idx, val_idx))
            
    return cv_folds
