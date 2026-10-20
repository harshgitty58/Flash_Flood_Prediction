"""Behaviour tests for the deployed XGBoost (PRAHAR_MASTER_PLAN.md WS-20.6, WS-08.5)."""
import joblib
import numpy as np
import pytest

from src.config import PROJECT_ROOT
from src.data_loader import FEATURE_EXPERIMENTS, FINAL_EXPERIMENT, load_ml_dataset
from src.model_config import TARGET_COL

FEATS = FEATURE_EXPERIMENTS[FINAL_EXPERIMENT]


@pytest.fixture(scope="module")
def model():
    return joblib.load(PROJECT_ROOT / "models/xgboost/model.joblib")


@pytest.fixture(scope="module")
def X():
    ds = load_ml_dataset()
    d = ds[(ds["datetime"] >= "2023-07-01") & (ds["datetime"] < "2023-08-26") & ds[TARGET_COL].notna()]
    return d[FEATS].sample(2000, random_state=0).reset_index(drop=True)


def test_deterministic_and_row_order_invariant(model, X):
    p = model.predict_proba(X)[:, 1]
    assert np.array_equal(p, model.predict_proba(X)[:, 1])
    perm = np.random.default_rng(1).permutation(len(X))
    assert np.allclose(model.predict_proba(X.iloc[perm])[:, 1], p[perm])


def test_shap_values_add_up_to_the_margin(model, X):
    shap = pytest.importorskip("shap")
    pre, clf = model.named_steps["preprocessor"], model.named_steps["classifier"]
    Xt = pre.transform(X)
    explainer = shap.TreeExplainer(clf)          # one explainer: expected_value belongs to the same call
    sv = explainer.shap_values(Xt)
    margin = clf.predict(Xt, output_margin=True)
    assert np.allclose(sv.sum(1) + explainer.expected_value, margin, atol=1e-3)


def test_probabilities_are_valid(model, X):
    p = model.predict_proba(X)[:, 1]
    assert np.isfinite(p).all() and (p >= 0).all() and (p <= 1).all()


@pytest.mark.xfail(strict=True, reason="V-38: the unconstrained model lowers risk for more rain in ~3 % of hours; "
                                       "monotone constraints fix it but cost test PR-AUC (results/v3/v38_monotone.md)")
def test_more_rain_never_lowers_risk(model, X):
    p0 = model.predict_proba(X)[:, 1]
    X2 = X.copy()
    for c in ("rain_24h", "rain_48h", "rain_72h"):
        X2[c] = X2[c] + 20
    assert (model.predict_proba(X2)[:, 1] >= p0 - 1e-9).all()
