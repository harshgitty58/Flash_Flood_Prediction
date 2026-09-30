"""
Model Training and Hyperparameter Tuning Module for Phase 3.
Implements bounded, time-aware search across Logistic Regression, Random Forest, and XGBoost.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Tuple
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit
from src.model_config import TUNING_DIR, RANDOM_STATE
from src.preprocessing import get_logistic_preprocessor, get_tree_preprocessor, calculate_scale_pos_weight
from sklearn.pipeline import Pipeline

def tune_logistic_regression(X_train: pd.DataFrame, y_train: pd.Series) -> Tuple[Pipeline, Dict[str, Any], pd.DataFrame]:
    """Tunes Logistic Regression using TimeSeriesSplit on training data only."""
    TUNING_DIR.mkdir(parents=True, exist_ok=True)
    
    pipe = Pipeline([
        ("preprocessor", get_logistic_preprocessor()),
        ("classifier", LogisticRegression(random_state=RANDOM_STATE, max_iter=1000)),
    ])
    
    param_grid = {
        "classifier__C": [0.01, 0.1, 1.0, 5.0, 10.0],
        "classifier__penalty": ["l2"],
        "classifier__solver": ["lbfgs", "liblinear"],
        "classifier__class_weight": ["balanced", None],
    }
    
    cv = TimeSeriesSplit(n_splits=3)
    search = RandomizedSearchCV(
        pipe,
        param_distributions=param_grid,
        n_iter=8,
        scoring="balanced_accuracy",
        cv=cv,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    search.fit(X_train, y_train)
    
    # Save search results and best parameters
    results_df = pd.DataFrame(search.cv_results_)
    results_df.to_csv(TUNING_DIR / "logistic_regression_search.csv", index=False)
    
    with open(TUNING_DIR / "logistic_regression_best_params.json", "w", encoding="utf-8") as f:
        json.dump(search.best_params_, f, indent=2, default=str)
        
    return search.best_estimator_, search.best_params_, results_df

def tune_random_forest(X_train: pd.DataFrame, y_train: pd.Series) -> Tuple[Pipeline, Dict[str, Any], pd.DataFrame]:
    """Tunes Random Forest using TimeSeriesSplit on training data only."""
    TUNING_DIR.mkdir(parents=True, exist_ok=True)
    
    pipe = Pipeline([
        ("preprocessor", get_tree_preprocessor()),
        ("classifier", RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=-1)),
    ])
    
    param_grid = {
        "classifier__n_estimators": [100, 200],
        "classifier__max_depth": [5, 10, 15, None],
        "classifier__min_samples_split": [2, 5, 10],
        "classifier__min_samples_leaf": [1, 2, 4],
        "classifier__class_weight": ["balanced", "balanced_subsample", None],
    }
    
    cv = TimeSeriesSplit(n_splits=3)
    search = RandomizedSearchCV(
        pipe,
        param_distributions=param_grid,
        n_iter=8,
        scoring="balanced_accuracy",
        cv=cv,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    search.fit(X_train, y_train)
    
    results_df = pd.DataFrame(search.cv_results_)
    results_df.to_csv(TUNING_DIR / "random_forest_search.csv", index=False)
    
    with open(TUNING_DIR / "random_forest_best_params.json", "w", encoding="utf-8") as f:
        json.dump(search.best_params_, f, indent=2, default=str)
        
    return search.best_estimator_, search.best_params_, results_df

def tune_xgboost(X_train: pd.DataFrame, y_train: pd.Series) -> Tuple[Pipeline, Dict[str, Any], pd.DataFrame]:
    """Tunes XGBoost using TimeSeriesSplit on training data only."""
    TUNING_DIR.mkdir(parents=True, exist_ok=True)
    scale_pos = calculate_scale_pos_weight(y_train)
    
    pipe = Pipeline([
        ("preprocessor", get_tree_preprocessor()),
        ("classifier", XGBClassifier(
            random_state=RANDOM_STATE,
            eval_metric="logloss",
            n_jobs=-1,
        )),
    ])
    
    param_grid = {
        "classifier__n_estimators": [100, 200],
        "classifier__max_depth": [3, 5, 7],
        "classifier__learning_rate": [0.01, 0.05, 0.1],
        "classifier__subsample": [0.8, 1.0],
        "classifier__colsample_bytree": [0.8, 1.0],
        "classifier__scale_pos_weight": [1.0, scale_pos],
    }
    
    cv = TimeSeriesSplit(n_splits=3)
    search = RandomizedSearchCV(
        pipe,
        param_distributions=param_grid,
        n_iter=8,
        scoring="balanced_accuracy",
        cv=cv,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    search.fit(X_train, y_train)
    
    results_df = pd.DataFrame(search.cv_results_)
    results_df.to_csv(TUNING_DIR / "xgboost_search.csv", index=False)
    
    with open(TUNING_DIR / "xgboost_best_params.json", "w", encoding="utf-8") as f:
        json.dump(search.best_params_, f, indent=2, default=str)
        
    return search.best_estimator_, search.best_params_, results_df
