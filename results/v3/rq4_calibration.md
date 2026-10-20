# RQ4: calibration and conformal study (deployed XGBoost scores)

Calibrate on July 2023 (20,280 hours, 864 flood hours); evaluate on 1–25 Aug 2023 (12,469 hours, 720 flood hours). Rule fixed before the run: see `src/calibration_study.py`.

**Why the probabilities look quantised:** the model itself emits only 109 distinct raw scores on the test month, and 72 % of all test hours share the single most common score. Calibration can only re-map those levels; more resolution needs a finer model (WS-05.6: more trees with early stopping).

| calibrator      |   log_loss |   brier |    ece |   distinct_values |   roc_auc |   cov90_flood |   cov90_no_flood |   singleton_90 | nested   | levels_distinct   |
|:----------------|-----------:|--------:|-------:|------------------:|----------:|--------------:|-----------------:|---------------:|:---------|:------------------|
| raw             |    0.33831 | 0.09282 | 0.1841 |               109 |    0.7076 |             1 |           0.8959 |         0.1304 | True     | True              |
| platt           |    0.19986 | 0.0518  | 0.0133 |               109 |    0.7076 |             1 |           0.8959 |         0.1304 | True     | True              |
| beta            |    0.19858 | 0.05156 | 0.0133 |               109 |    0.7076 |             1 |           0.8959 |         0.1304 | True     | True              |
| isotonic        |    0.20372 | 0.05187 | 0.0309 |                 8 |    0.71   |             1 |           0.8959 |         0.1303 | True     | True              |
| ivap (deployed) |    0.20348 | 0.05179 | 0.0311 |                22 |    0.71   |             1 |           0.877  |         0.149  | True     | True              |
| cvap            |    0.20361 | 0.05184 | 0.031  |                37 |    0.7051 |             1 |           0.877  |         0.149  | True     | True              |

**Decision:** candidate(s) passing the rule: ['platt', 'beta']; recorded for v1.0, to be re-checked on protocol P-2 before deployment.
