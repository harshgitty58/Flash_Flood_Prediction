# PRAHAR: label work, before and after

Baseline v0 was frozen before any label change (`results/baseline_v0/`). Every number below uses the same splits, the same 23 features (Exp_G), the same tuning search and the same verification code; only the labels differ.

## L0: district-name fix in the label join

The IMD inventory spells *Rudra Prayag*, *Udam Singh Nagar* and *Garhwal* (the Census name of Pauri Garhwal), while the station table spells *Rudraprayag*, *Udham Singh Nagar* and *Pauri Garhwal*. The label join is an exact string match, so 13 of the 29 IMD event-days in 2022–23 were silently scored as 'no flood'. Rudraprayag, the most flood-hit district in the window, had 0 positives.

| split | positives (station-hours) now |
|---|---|
| train | 367 of 94,154 |
| validation | 864 of 20,280 |
| test | 720 of 12,469 |

Before L0, the positives were 271 (train), 384 (validation) and 240 (test).

### Held-out test (Aug 2023), station-hour

| model | roc_auc | pr_auc | precision | recall | f1 | mcc | brier |
|---|---|---|---|---|---|---|---|
| Logistic Regression | 0.451 → **0.741** | 0.038 → **0.139** | 0.076 → **0.169** | 0.329 → **0.211** | 0.124 → **0.188** | 0.125 → **0.133** | 0.071 → **0.123** |
| Random Forest | 0.595 → **0.788** | 0.088 → **0.152** | 0.147 → **0.173** | 0.133 → **0.369** | 0.140 → **0.236** | 0.124 → **0.185** | 0.018 → **0.096** |
| XGBoost | 0.534 → **0.708** | 0.036 → **0.150** | 0.060 → **0.222** | 0.125 → **0.574** | 0.082 → **0.320** | 0.061 → **0.295** | 0.068 → **0.093** |

### Verification at ≥ ALERT on the test month (WMO categorical scores)

| unit | layer | events | POD | FAR | CSI | HSS |
|---|---|---|---|---|---|---|
| station-hour | hybrid (deployed) | 240 → 720 | 0.471 → **0.650** | 0.881 → **0.766** | 0.105 → **0.208** | 0.165 → **0.283** |
| station-hour | ML only | 240 → 720 | 0.275 → **0.574** | 0.918 → **0.778** | 0.068 → **0.191** | 0.100 → **0.259** |
| station-hour | rainfall rule only | 240 → 720 | 0.250 → **0.083** | 0.620 → **0.620** | 0.178 → **0.073** | 0.291 → **0.118** |
| station-hour | district prior only | 240 → 720 | 1.000 → **1.000** | 0.981 → **0.942** | 0.019 → **0.058** | 0.000 → **0.000** |
| district-day | hybrid (deployed) | 4 → 10 | 0.750 → **0.700** | 0.939 → **0.901** | 0.060 → **0.095** | 0.089 → **0.117** |
| district-day | ML only | 4 → 10 | 0.250 → **0.500** | 0.960 → **0.900** | 0.036 → **0.091** | 0.045 → **0.113** |
| district-day | rainfall rule only | 4 → 10 | 0.750 → **0.300** | 0.897 → **0.897** | 0.100 → **0.083** | 0.160 → **0.106** |
| district-day | district prior only | 4 → 10 | 1.000 → **1.000** | 0.986 → **0.964** | 0.014 → **0.036** | 0.000 → **0.000** |
| district-day | persistence (flood yesterday) | 4 → 10 | 0.000 → **0.100** | 1.000 → **0.900** | 0.000 → **0.053** | -0.015 → **0.066** |

### Leave-one-event-out CV (XGBoost)

| experiment | folds | positives | pooled_roc_auc | pooled_pr_auc | base_rate | min_fold_roc_auc |
|---|---|---|---|---|---|---|
| Exp_A_Rainfall_Only | 6 | 1248 | 0.4971 | 0.0929 | 0.0807 | 0.3467 |
| Exp_B_Rainfall_Discharge | 6 | 1248 | 0.5477 | 0.1012 | 0.0807 | 0.4508 |
| Exp_C_Rainfall_Discharge_FloodHist | 6 | 1248 | 0.7724 | 0.2226 | 0.0807 | 0.6286 |
| Exp_D_Rainfall_Discharge_Flood_Landslide | 6 | 1248 | 0.7715 | 0.2364 | 0.0807 | 0.5679 |
| Exp_E_Full_Multimodal | 6 | 1248 | 0.6546 | 0.1412 | 0.0807 | 0.5 |
| Exp_F_No_Location | 6 | 1248 | 0.6138 | 0.126 | 0.0807 | 0.3786 |
| Exp_G_Static_History | 6 | 1248 | 0.7008 | 0.1856 | 0.0807 | 0.5801 |
| Exp_H_Multisource | 6 | 1248 | 0.7032 | 0.1466 | 0.0807 | 0.5846 |
| Exp_T_Trigger_Only | 6 | 1248 | 0.6016 | 0.1038 | 0.0807 | 0.4728 |

Before L0, Exp_G scored a pooled ROC-AUC of 0.858 on event-CV. That number was inflated: all positives came from 5 districts, so the static district features could pick out 'the districts that have labels'. After the fix, event-CV (0.70) and the held-out test (0.71) agree. Exp_C/D score higher on event-CV, but they rely on the IMD flood-history features, which stop updating when the inventory ends (2023-08). They cannot be deployed for 2024+, so Exp_G stays the deployed set.

## Label audit: IMD vs SANDRP (2022 – Aug 2023)

- IMD events 26, SANDRP events 48; IMD days also reported by SANDRP: 8/28.
- **SANDRP-only events: 40**, i.e. damaging events that are missing from the training labels (by split: {'train': 22, 'test': 12, 'validation': 8}). On 6/20 of the validation/test SANDRP-only days the deployed hybrid already alerted, and v1 scores those alerts as false alarms.
- Decision gate (sandrp_only_events >= 25% of imd_events): share 1.538, passed = **True**.

## Label v2 experiment (XGBoost; 2×2 train-label × truth grid)

| trained_on | scored_on | threshold | roc_auc | pr_auc | precision | recall | f1 | test_base_rate | dd_POD | dd_FAR | dd_CSI | dd_CSI_ci95 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v1 | v1 | 0.25 | 0.7076 | 0.1501 | 0.2223 | 0.5736 | 0.3204 | 0.0577 | 0.474 | 0.82 | 0.15 | [0.085, 0.223] |
| v1 | v2 | 0.25 | 0.647 | 0.2059 | 0.3428 | 0.4694 | 0.3963 | 0.1088 | 0.4 | 0.72 | 0.197 | [0.124, 0.292] |
| v1 | v2_masked | 0.25 | 0.6421 | 0.2157 | 0.3595 | 0.4694 | 0.4072 | 0.1191 | 0.4 | 0.696 | 0.209 | [0.129, 0.305] |
| v2 | v1 | 0.65 | 0.6858 | 0.1126 | 0.122 | 0.2444 | 0.1627 | 0.0577 | 0.368 | 0.857 | 0.115 | [0.051, 0.183] |
| v2 | v2 | 0.65 | 0.6371 | 0.1844 | 0.2426 | 0.2579 | 0.25 | 0.1088 | 0.343 | 0.755 | 0.167 | [0.097, 0.253] |
| v2 | v2_masked | 0.65 | 0.6338 | 0.1982 | 0.2684 | 0.2579 | 0.2631 | 0.1191 | 0.343 | 0.733 | 0.176 | [0.105, 0.265] |
| v2_masked | v1 | 0.7 | 0.6865 | 0.1135 | 0.122 | 0.2444 | 0.1627 | 0.0577 | 0.368 | 0.857 | 0.115 | [0.051, 0.183] |
| v2_masked | v2 | 0.7 | 0.6363 | 0.1826 | 0.2426 | 0.2579 | 0.25 | 0.1088 | 0.343 | 0.755 | 0.167 | [0.097, 0.253] |
| v2_masked | v2_masked | 0.7 | 0.6332 | 0.1968 | 0.2684 | 0.2579 | 0.2631 | 0.1191 | 0.343 | 0.733 | 0.176 | [0.105, 0.265] |

Event-CV with each version's own truth:

| labels | episodes | folds | pooled_roc_auc | pooled_pr_auc | base_rate |
|---|---|---|---|---|---|
| v1 | 6.0 | 6.0 | 0.7006 | 0.1879 | 0.0807 |
| v2 | 8.0 | 8.0 | 0.7814 | 0.3642 | 0.147 |
| v2_masked | 8.0 | 8.0 | 0.7557 | 0.3881 | 0.1875 |

Decision rule: adopt v2 if, for XGBoost, the v2-trained model is at least as good as v1-trained on BOTH truths (PR-AUC and district-day CSI) and event-CV PR-AUC improves.

Result: v2 on v1 truth ok = False, v2 on v2 truth ok = False, event-CV ok = True, so **adopt v2 = False**.

## External validation (events after the training labels end)

- 29 documented events (2023-09-15..2025-09-17); 21 had a reporting gauge in the district.
- Hybrid ≥ ALERT POD: 7/21 = 0.333 (95 % CI [0.143, 0.524]); ML-only 0.143; rainfall-only 0.286.
- Alert burden (ALERT+ district-days per monsoon; share within ±2 days of a documented event): 2023: 84 (0%); 2024: 370 (5%); 2025: 171 (5%); 2026: 318 (0%)
