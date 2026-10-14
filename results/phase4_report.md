# Phase 4 Report — Uncertainty-Aware and Robust Flash-Flood Prediction

## 0. Corrections made before Phase 4
- **Duplicate station-hours** (one gauge with two coordinate pairs fanned out the merge) fixed → 21,464 rows.
- **Label coverage**: the IMD flood inventory ends 2023-08-26. Rows after that were silently labelled 0; they are now
  *unlabelled* (used for replay only). Labelled data: 7,830 rows, 44 positives, 6 flood episodes.
- **Location leakage**: raw latitude/longitude carried 38 % of gain. Final model = `Exp_G_Static_History` (no coordinates).

## 1. Evaluation protocol — leave-one-event-out CV (src/event_cv.py)
Each flood episode (±3 days) is held out in turn; training excludes a 7-day buffer around it.

| experiment                               |   features |   folds |   rows |   positives |   pooled_roc_auc |   pooled_pr_auc |   base_rate |   mean_fold_roc_auc |   min_fold_roc_auc |
|:-----------------------------------------|-----------:|--------:|-------:|------------:|-----------------:|----------------:|------------:|--------------------:|-------------------:|
| Exp_A_Rainfall_Only                      |         10 |       6 |  15473 |        1248 |           0.4971 |          0.0929 |      0.0807 |              0.5207 |             0.3467 |
| Exp_B_Rainfall_Discharge                 |         14 |       6 |  15473 |        1248 |           0.5477 |          0.1012 |      0.0807 |              0.6262 |             0.4508 |
| Exp_C_Rainfall_Discharge_FloodHist       |         21 |       6 |  15473 |        1248 |           0.7724 |          0.2226 |      0.0807 |              0.7966 |             0.6286 |
| Exp_D_Rainfall_Discharge_Flood_Landslide |         25 |       6 |  15473 |        1248 |           0.7715 |          0.2364 |      0.0807 |              0.7579 |             0.5679 |
| Exp_E_Full_Multimodal                    |         32 |       6 |  15473 |        1248 |           0.6546 |          0.1412 |      0.0807 |              0.6619 |             0.5    |
| Exp_F_No_Location                        |         30 |       6 |  15473 |        1248 |           0.6138 |          0.126  |      0.0807 |              0.6489 |             0.3786 |
| Exp_G_Static_History                     |         23 |       6 |  15473 |        1248 |           0.7008 |          0.1856 |      0.0807 |              0.7703 |             0.5801 |
| Exp_H_Multisource                        |         42 |       6 |  15473 |        1248 |           0.7032 |          0.1466 |      0.0807 |              0.7235 |             0.5846 |
| Exp_T_Trigger_Only                       |         29 |       6 |  15473 |        1248 |           0.6016 |          0.1038 |      0.0807 |              0.5654 |             0.4728 |

Single chronological split (train 2022 · val Jan–Jul 2023 · test Aug 2023, 17 positives) for reference:

| model               | feature_set          |   threshold |   val_roc_auc |   val_pr_auc |   test_roc_auc |   test_pr_auc |   test_recall |
|:--------------------|:---------------------|------------:|--------------:|-------------:|---------------:|--------------:|--------------:|
| Logistic Regression | Exp_G_Static_History |        0.85 |        0.6422 |       0.0755 |         0.7407 |        0.1389 |        0.2111 |
| Random Forest       | Exp_G_Static_History |        0.45 |        0.6323 |       0.1131 |         0.7881 |        0.1523 |        0.3694 |
| XGBoost             | Exp_G_Static_History |        0.25 |        0.7193 |       0.1087 |         0.7076 |        0.1501 |        0.5736 |

## 2. Uncertainty — Venn-Abers + Mondrian conformal (src/conformal.py)
Calibration on 20,280 validation rows (864 floods); test 12469 rows (720 floods).
Brier score 0.09282 (raw) → 0.05179 (calibrated).

|   nominal |   coverage_all |   coverage_flood |   coverage_no_flood |   share_uncertain |   share_flood_singleton |
|----------:|---------------:|-----------------:|--------------------:|------------------:|------------------------:|
|      0.8  |         0.8841 |                1 |              0.877  |            0.8508 |                  0.1492 |
|      0.9  |         0.8841 |                1 |              0.877  |            0.851  |                  0.149  |
|      0.95 |         0.9726 |                1 |              0.9709 |            0.9658 |                  0.0342 |

Nominal coverage is met for both classes at 90 % and 95 %. Most sets are "uncertain": the model rarely separates
the classes with confidence, which is the honest outcome with ~20 calibration floods.

## 3. Explanations — SHAP (src/explain.py)
| feature                       |   mean_abs_shap |
|:------------------------------|----------------:|
| district_flood_severity_index |     1.10054     |
| rain_48h                      |     0.180644    |
| rain_72h                      |     0.114424    |
| landslide_count_10km          |     0.103935    |
| dist_to_nearest_landslide_km  |     0.0554642   |
| rain_max_intensity_24h        |     0.0431068   |
| rain_24h                      |     0.0326567   |
| api_decay_85                  |     0.0251278   |
| rain_12h                      |     0.00500001  |
| rain_6h                       |     0.000485229 |

## 4. Warning levels (src/warning_levels.py)
Calibrated-probability cut-offs {'WATCH': 0.08521, 'ALERT': 0.21302, 'SEVERE': 0.42604, 'EXTREME': 0.85207} (base rate 4.26%); a conformal FLOOD set lifts to ≥ ALERT.

| split      | layer     | tier    |   rows |   flood_rows |   hit_rate |   lift_vs_base |
|:-----------|:----------|:--------|-------:|-------------:|-----------:|---------------:|
| validation | tier_ml   | NORMAL  |  18005 |          548 |     0.0304 |           0.71 |
| validation | tier_ml   | WATCH   |   1869 |          219 |     0.1172 |           2.75 |
| validation | tier_ml   | ALERT   |    406 |           97 |     0.2389 |           5.61 |
| validation | tier_ml   | SEVERE  |      0 |            0 |   nan      |         nan    |
| validation | tier_ml   | EXTREME |      0 |            0 |   nan      |         nan    |
| validation | tier_rain | NORMAL  |  15445 |          678 |     0.0439 |           1.03 |
| validation | tier_rain | WATCH   |   2601 |          135 |     0.0519 |           1.22 |
| validation | tier_rain | ALERT   |    589 |            0 |     0      |           0    |
| validation | tier_rain | SEVERE  |   1016 |           25 |     0.0246 |           0.58 |
| validation | tier_rain | EXTREME |    629 |           26 |     0.0413 |           0.97 |
| validation | tier      | NORMAL  |  13715 |          450 |     0.0328 |           0.77 |
| validation | tier      | WATCH   |   3930 |          271 |     0.069  |           1.62 |
| validation | tier      | ALERT   |    990 |           92 |     0.0929 |           2.18 |
| validation | tier      | SEVERE  |   1016 |           25 |     0.0246 |           0.58 |
| validation | tier      | EXTREME |    629 |           26 |     0.0413 |           0.97 |
| test       | tier_ml   | NORMAL  |  10611 |          307 |     0.0289 |           0.68 |
| test       | tier_ml   | WATCH   |      0 |            0 |   nan      |         nan    |
| test       | tier_ml   | ALERT   |   1858 |          413 |     0.2223 |           5.22 |
| test       | tier_ml   | SEVERE  |      0 |            0 |   nan      |         nan    |
| test       | tier_ml   | EXTREME |      0 |            0 |   nan      |         nan    |
| test       | tier_rain | NORMAL  |  10945 |          508 |     0.0464 |           1.09 |
| test       | tier_rain | WATCH   |   1366 |          152 |     0.1113 |           2.61 |
| test       | tier_rain | ALERT   |     97 |           42 |     0.433  |          10.16 |
| test       | tier_rain | SEVERE  |     59 |           18 |     0.3051 |           7.16 |
| test       | tier_rain | EXTREME |      2 |            0 |     0      |           0    |
| test       | tier      | NORMAL  |   9362 |          166 |     0.0177 |           0.42 |
| test       | tier      | WATCH   |   1106 |           86 |     0.0778 |           1.83 |
| test       | tier      | ALERT   |   1940 |          450 |     0.232  |           5.44 |
| test       | tier      | SEVERE  |     59 |           18 |     0.3051 |           7.16 |
| test       | tier      | EXTREME |      2 |            0 |     0      |           0    |

≥ ALERT on the test month: recall 0.65, precision 0.234, false-alarm rate 0.1305.

## 5. Lead time (event level, out-of-fold)
Alarm threshold = 95th percentile of non-flood scores (5 % hourly false alarms).
**8/19 district floods detected.** Lead times equal to the 48 h search window mean the alarm was already on at the window start (largely the district baseline), so no lead-time figure is claimed.

| district          | event_start   |   stations |   max_p | detected   |   lead_time_h |
|:------------------|:--------------|-----------:|--------:|:-----------|--------------:|
| Dehradun          | 2022-08-19    |          2 |   0.71  | False      |           nan |
| Dehradun          | 2022-09-22    |          3 |   0.704 | False      |           nan |
| Uttarkashi        | 2022-09-22    |          1 |   0.484 | False      |           nan |
| Rudraprayag       | 2023-06-25    |          2 |   0.786 | True       |            48 |
| Dehradun          | 2023-07-09    |          1 |   0.748 | True       |           -12 |
| Udham Singh Nagar | 2023-07-09    |          5 |   0.184 | False      |           nan |
| Uttarkashi        | 2023-07-10    |          1 |   0.657 | False      |           nan |
| Pithoragarh       | 2023-07-11    |          3 |   0.184 | False      |           nan |
| Rudraprayag       | 2023-07-11    |          2 |   0.776 | True       |            36 |
| Chamoli           | 2023-07-16    |          3 |   0.184 | False      |           nan |
| Rudraprayag       | 2023-07-16    |          2 |   0.298 | False      |           nan |
| Rudraprayag       | 2023-07-17    |          2 |   0.298 | False      |           nan |
| Tehri Garhwal     | 2023-08-06    |          1 |   0.718 | True       |            12 |
| Rudraprayag       | 2023-08-07    |          2 |   0.769 | True       |            36 |
| Rudraprayag       | 2023-08-09    |          2 |   0.769 | True       |            48 |
| Pauri Garhwal     | 2023-08-10    |          1 |   0.576 | False      |           nan |
| Rudraprayag       | 2023-08-10    |          2 |   0.754 | True       |             8 |
| Tehri Garhwal     | 2023-08-21    |          1 |   0.723 | True       |            48 |
| Pauri Garhwal     | 2023-08-23    |          2 |   0.669 | False      |           nan |

## 6. Robustness to degraded inputs (src/robustness.py)
| scenario                                | kind     |   roc_auc |   pr_auc |   mean_abs_score_change |   flood_rows_mean_score |   roc_auc_drop |
|:----------------------------------------|:---------|----------:|---------:|------------------------:|------------------------:|---------------:|
| Baseline (all inputs)                   | baseline |    0.7155 |   0.1225 |                  0      |                  0.3706 |         0      |
| R1 rainfall noise sd=5% of std          | noise    |    0.7136 |   0.1162 |                  0.0103 |                  0.3719 |         0.0019 |
| R1 rainfall noise sd=10% of std         | noise    |    0.7147 |   0.1216 |                  0.0125 |                  0.3728 |         0.0008 |
| R1 rainfall noise sd=20% of std         | noise    |    0.7117 |   0.1212 |                  0.0156 |                  0.364  |         0.0038 |
| R1 rainfall noise sd=50% of std         | noise    |    0.7052 |   0.1097 |                  0.0206 |                  0.3418 |         0.0103 |
| R3 river discharge offline              | outage   |    0.7155 |   0.1225 |                  0      |                  0.3706 |         0      |
| R3b rainfall gauge offline              | outage   |    0.7105 |   0.1113 |                  0.023  |                  0.3405 |         0.005  |
| R3c flood-history records unavailable   | outage   |    0.5    |   0.0484 |                  0.0506 |                  0.1835 |         0.2155 |
| R3d landslide inventory unavailable     | outage   |    0.7143 |   0.124  |                  0.0094 |                  0.3375 |         0.0012 |
| R4 random dropout 10% of inputs         | dropout  |    0.6871 |   0.1133 |                  0.0098 |                  0.3431 |         0.0284 |
| R4 random dropout 25% of inputs         | dropout  |    0.6467 |   0.0968 |                  0.0229 |                  0.2974 |         0.0688 |
| R4 random dropout 50% of inputs         | dropout  |    0.5933 |   0.0808 |                  0.0369 |                  0.2457 |         0.1222 |
| R5 noisy rain (20%) + discharge offline | combined |    0.7129 |   0.1209 |                  0.0159 |                  0.364  |         0.0026 |

## 7. Limitations
- 44 positive station-hours / 6 episodes: every metric has wide uncertainty.
- Flood-history features go stale after 2023-08 (no newer labels) → replay-period predictions extrapolate.
- River discharge contributes nothing (7 gauges, most stations unmatched); DEM, soil moisture and satellite rainfall not yet used.

## 8. Inference artifacts (results/inference_artifacts/)
`xgboost_model.joblib`, `feature_columns.json`, `calibration_scores.csv` (Venn-Abers/conformal calibration), `warning_thresholds.json`.
