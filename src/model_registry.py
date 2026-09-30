"""
Model Registry and Artifact Serialization Module for Phase 3.
Persists trained models to models/<model_name>/model.joblib and logs metadata.
"""

import json
import joblib
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Tuple
from src.model_config import MODELS_DIR, RESULTS_DIR

REGISTRY_CSV = RESULTS_DIR / "model_registry.csv"

def save_model_artifact(
    model: Any,
    model_name: str,
    feature_list: List[str],
    hyperparameters: Dict[str, Any],
    metrics: Dict[str, Any],
    threshold: float,
    train_range: Tuple[str, str],
    notes: str = "",
) -> Path:
    """Serializes a trained model to joblib and outputs structured metadata.json."""
    model_dir = MODELS_DIR / model_name.lower().replace(" ", "_")
    model_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Save joblib artifact
    model_path = model_dir / "model.joblib"
    joblib.dump(model, model_path)
    
    # 2. Save metadata.json
    metadata = {
        "model_name": model_name,
        "feature_count": len(feature_list),
        "features": feature_list,
        "selected_hyperparameters": hyperparameters,
        "validation_metrics": metrics,
        "operating_threshold": threshold,
        "training_start_date": train_range[0],
        "training_end_date": train_range[1],
        "notes": notes,
    }
    
    meta_path = model_dir / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, default=str)
        
    # 3. Update master model_registry.csv
    record = {
        "model_id": f"{model_name.lower()}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}",
        "model_name": model_name,
        "feature_set": f"{len(feature_list)} features",
        "train_start": train_range[0],
        "train_end": train_range[1],
        "threshold": threshold,
        "val_roc_auc": metrics.get("roc_auc"),
        "val_pr_auc": metrics.get("pr_auc"),
        "val_f1": metrics.get("f1"),
        "model_path": str(model_path.relative_to(MODELS_DIR.parent)),
        "notes": notes,
    }
    
    if REGISTRY_CSV.exists():
        reg_df = pd.read_csv(REGISTRY_CSV)
        reg_df = pd.concat([reg_df, pd.DataFrame([record])], ignore_index=True)
    else:
        reg_df = pd.DataFrame([record])
        
    reg_df.to_csv(REGISTRY_CSV, index=False)
    print(f"Model saved: {model_path} with metadata at {meta_path}")
    return model_path
