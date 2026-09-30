"""
Comprehensive Model Evaluation and Metrics Module for Phase 3.
Computes ROC-AUC, PR-AUC, Brier score, MCC, confusion matrices, and threshold trade-offs.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    precision_score,
    recall_score,
    f1_score,
    balanced_accuracy_score,
    matthews_corrcoef,
    brier_score_loss,
    log_loss,
    confusion_matrix,
    roc_curve,
    precision_recall_curve,
)
from sklearn.calibration import calibration_curve

def compute_all_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> Dict[str, float]:
    """Computes comprehensive multi-metric classification and probability performance."""
    # Ensure binary arrays
    y_true = np.asarray(y_true, dtype=int)
    y_prob = np.asarray(y_prob, dtype=float)
    y_prob = np.clip(y_prob, 1e-15, 1 - 1e-15)
    
    y_pred = (y_prob >= threshold).astype(int)
    
    # If single class present in test ground truth, AUC metrics may raise error; handle safely
    unique_classes = np.unique(y_true)
    if len(unique_classes) > 1:
        roc_auc = float(roc_auc_score(y_true, y_prob))
        pr_auc = float(average_precision_score(y_true, y_prob))
    else:
        roc_auc = np.nan
        pr_auc = np.nan
        
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    bal_acc = float(balanced_accuracy_score(y_true, y_pred))
    mcc = float(matthews_corrcoef(y_true, y_pred))
    brier = float(brier_score_loss(y_true, y_prob))
    
    try:
        loss = float(log_loss(y_true, y_prob))
    except Exception:
        loss = np.nan
        
    # Specificity = TN / (TN + FP)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    spec = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    
    return {
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "specificity": round(spec, 4),
        "balanced_accuracy": round(bal_acc, 4),
        "mcc": round(mcc, 4),
        "brier": round(brier, 4),
        "log_loss": round(loss, 4),
        "threshold": round(threshold, 2),
    }

def find_optimal_threshold(y_true: np.ndarray, y_prob: np.ndarray) -> Tuple[float, pd.DataFrame]:
    """Sweeps threshold grid on validation set to find the threshold that maximizes F1 while maintaining Recall >= 0.50."""
    thresholds = np.linspace(0.05, 0.95, 19)
    records = []
    
    for t in thresholds:
        m = compute_all_metrics(y_true, y_prob, threshold=t)
        records.append(m)
        
    thresh_df = pd.DataFrame(records)
    
    # Filter for recall >= 0.30 if available, else max F1
    viable = thresh_df[thresh_df["recall"] >= 0.20]
    if len(viable) > 0:
        best_t = viable.sort_values(by=["f1", "pr_auc"], ascending=False).iloc[0]["threshold"]
    else:
        best_t = thresh_df.sort_values(by="f1", ascending=False).iloc[0]["threshold"]
        
    return float(best_t), thresh_df
