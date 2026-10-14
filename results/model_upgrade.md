# PRAHAR: model upgrade experiments (MODEL_UPGRADE_PLAN.md)

Every adoption rule is written in the module docstring before the first run; the same splits and verification code are used throughout.

## E1: equal-weight ensemble (LR + RF + XGBoost, percentile-averaged)

| Model | ROC-AUC v1 | PR-AUC v1 | Day CSI v1 | PR-AUC v2 | Day CSI v2 |
|---|---|---|---|---|---|
| xgb | 0.7076 | 0.1501 | 0.15 | 0.2059 | 0.197 |
| rf | 0.7881 | 0.1523 | 0.15 | 0.2329 | 0.197 |
| ens | 0.7842 | 0.1511 | 0.145 | 0.2323 | 0.192 |

Event-CV pooled PR-AUC: XGBoost 0.1879, ensemble 0.2046 (ROC 0.7006 → 0.7321).
Decision: **adopt = False** {'event_cv_ok': True, 'test_v1_ok': False, 'test_v2_ok': False, 'adopt': False}. Ranking improves; district-day CSI does not.

## E2: rainfall thresholds fitted on documented events

Fit on 46 events (2022 – Jul 2023 and 2024). Hills, 24 h: ALERT 12.0 · SEVERE 42.4 · EXTREME 108.3 mm; 72 h: 22.4 · 87.0 · 177.8 mm (plains: too few events, so pooled values are used).
**Finding:** half of the documented floods had < 50 mm/24 h at the wettest gauge in their district, so most were local cloudbursts the gauge network did not record. Rain at the gauge cannot separate flood days from wet days.

| Rule | Test day POD | FAR | CSI | 2025 events POD | ALERT district-days 2024 / 2025 |
|---|---|---|---|---|---|
| current | 0.632 | 0.812 | 0.169 | 2/10 | 370 / 171 |
| fitted | 0.842 | 0.911 | 0.088 | 5/10 | 808 / 406 |

Decision: **adopt = False** {'csi_ok': False, 'pod_2025_ok': True, 'burden_ok': False, 'adopt': False}.

## E3: pooled district-day model + ranking view

Test ROC-AUC 0.753, PR-AUC 0.155 (base rate 0.068). As an alert layer at frequency bias 2: CSI 0.105 vs hybrid 0.169; external 3/29 vs hybrid 7/21.
Ranking, recall@3 (flooded district among the day's top 3): test 0.455 vs district prior 0.409; external events 0.345 vs prior 0.207 (chance 0.231).
Decision: alert layer adopt = **False**; ranking view offered = **True** (Overview → 'Districts to watch').

## Conclusion

No alert-layer change beats the deployed hybrid under its pre-set rule. The limit is the labels (about 50 IMD flood district-days) and the gauge network's blindness to local cloudbursts, not the model class. Two things do improve and are kept as reported results: ranking (ensemble ROC-AUC 0.78; district ranking recall@3 0.34 vs 0.21 prior). Next steps are data: a complete 2024–25 event list (USDMA SEOC daily reports via RTI) and radar or satellite rain (IMD Doppler or GPM IMERG) that can see cloudbursts between gauges.