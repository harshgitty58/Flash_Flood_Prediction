# Phase 3 Data Leakage Audit Checklist

This audit verifies that the machine learning experiments in Phase 3 strictly respect causality and avoid future data leakage.

| Leakage Prevention Requirement | Verification Procedure | Status |
| :--- | :--- | :--- |
| **No future timestamps in features** | All rolling aggregations look strictly into the past ($t - k$ to $t$). | **VERIFIED** |
| **Historical disaster counts** | Filtered by event start dates strictly $< t$. | **VERIFIED** |
| **Train-only preprocessing** | Imputers and scalers fitted solely on the training partition ($< 2024-06-01$). | **VERIFIED** |
| **Untouched holdout test set** | Zero tuning, zero threshold selection, and zero feature selection performed on the test period ($\ge 2025-01-01$). | **VERIFIED** |
| **Class imbalance scaling** | `scale_pos_weight` and class weights computed solely from training labels. | **VERIFIED** |
| **Threshold freezing** | Decision thresholds selected on the validation set and frozen before test evaluation. | **VERIFIED** |
