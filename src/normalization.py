"""
Parameterised feature normalisation (D3).

Each feature gets a method suited to its distribution; parameters are fitted on the training window only,
stored on the transformer, and exported to results/preprocessing/normalization_params.json so the exact
transformation can be reproduced at inference time (backend /predict) without refitting.

  log_robust   x >= 0, heavy right tail (rainfall, discharge, API, counts of landslides):
               z = (log1p(x) - median) / IQR
  signed_log   can be negative, heavy tails (rainfall / discharge changes):
               z = (sign(x)·log1p|x| - median) / IQR
  zscore       roughly symmetric indices (district severity, flooded area %, distances):
               z = (x - mean) / std
  passthrough  binary flags
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

METHOD_BY_PREFIX = [
    ("rain_intensity_change", "signed_log"),
    ("discharge_change", "signed_log"),
    ("discharge_anomaly", "signed_log"),
    ("rain_", "log_robust"),
    ("era5_", "log_robust"),
    ("pct_", "passthrough"),
    ("agree_both", "passthrough"),
    ("api_", "log_robust"),
    ("discharge", "log_robust"),
    ("landslide_count", "log_robust"),
    ("district_population", "log_robust"),
    ("district_historical_fatalities", "log_robust"),
    ("is_", "passthrough"),
]


def method_for(feature: str) -> str:
    return next((m for p, m in METHOD_BY_PREFIX if feature.startswith(p)), "zscore")


def _pre(method: str, x: np.ndarray) -> np.ndarray:
    if method == "log_robust":
        return np.log1p(np.clip(x, 0, None))
    if method == "signed_log":
        return np.sign(x) * np.log1p(np.abs(x))
    return x


class FeatureNormalizer(BaseEstimator, TransformerMixin):
    """sklearn transformer; expects an imputed numeric array or DataFrame with known feature names."""

    def __init__(self, feature_names=None):
        self.feature_names = feature_names

    def fit(self, X, y=None):
        names = list(self.feature_names or getattr(X, "columns", range(np.asarray(X).shape[1])))
        A = np.asarray(X, dtype=float)
        self.params_ = []
        for j, f in enumerate(names):
            m = method_for(str(f))
            v = _pre(m, A[:, j])
            v = v[~np.isnan(v)]
            if m == "passthrough" or len(v) == 0:
                c, s = 0.0, 1.0
            elif m == "zscore":
                c, s = float(v.mean()), float(v.std())
            else:
                q1, med, q3 = np.percentile(v, [25, 50, 75])
                c, s = float(med), float(q3 - q1)
                if s == 0:  # mostly-zero rainfall: fall back to std so the tail still varies
                    s = float(v.std())
            self.params_.append({"feature": str(f), "method": m, "center": c, "scale": s if s > 0 else 1.0})
        return self

    def transform(self, X):
        A = np.asarray(X, dtype=float).copy()
        for j, p in enumerate(self.params_):
            A[:, j] = (_pre(p["method"], A[:, j]) - p["center"]) / p["scale"]
        return A

    def to_json(self, path: Path, fit_window: dict | None = None):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"fit_window": fit_window, "features": self.params_}, indent=2))

    @classmethod
    def from_json(cls, path: Path) -> "FeatureNormalizer":
        d = json.loads(Path(path).read_text())
        n = cls([p["feature"] for p in d["features"]])
        n.params_ = d["features"]
        return n


def params_table(path: Path) -> pd.DataFrame:
    return pd.DataFrame(json.loads(Path(path).read_text())["features"])
