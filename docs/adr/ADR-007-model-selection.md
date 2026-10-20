# ADR-007: How the v1.0 model is selected (fixed before any v1.0 tuning run)

**Status:** accepted 2026-10-21, before any v1.0 tuning run. The git history timestamps this commit.

## Context
- With about 50 flood district-days in training, single-split numbers move by more than the differences between models (validation CSI 0.05 vs test 0.17 for the same warnings).
- Choosing a model after looking at many test numbers would overfit the test month (a garden of forking paths).

## Decision
1. **Tuning** uses the event-grouped protocol P-1 only (flood events clustered, ±7-day buffer). The objective is mean fold PR-AUC − 0.5 × its standard deviation.
2. **Selection:** among the tuned candidates (LR, RF, XGBoost, plus any challenger), choose the highest **pooled PR-AUC on rolling-origin protocol P-2** (train on years ≤ Y−1, test on year Y).
3. **Ties**, meaning a difference inside the paired-bootstrap 95 % CI: prefer fewer features, then a monotone model, then lower latency.
4. **The frozen test season** (P-4, the 2025 monsoon) is scored **once**, after selection, and reported whatever it shows.
5. A candidate that adds a data source must also keep the robustness drop for "flood history removed" at ≤ 0.10 ROC-AUC (prior dominance, V-10).

## Consequences
- Fewer, slower decisions, but every reported number can be defended.
- Experiments that fail the rule are still reported, as `results/model_upgrade.md` and `results/v3/` already do.
