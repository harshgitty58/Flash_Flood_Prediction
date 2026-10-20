# V-38: monotone rain constraints (WS-05.7)

Question: does forcing 'more rain never lowers risk' cost skill? Same splits, features, preprocessing and hyper-parameters as the deployed XGBoost; only the monotone constraints differ. Rule fixed before the run: see `src/monotone_study.py`.

| model                |   val ROC |   val PR-AUC |   test ROC |   test PR-AUC |   test base rate |   distinct test scores | rain +5mm: score falls   | rain +20mm: score falls   | rain +50mm: score falls   |
|:---------------------|----------:|-------------:|-----------:|--------------:|-----------------:|-----------------------:|:-------------------------|:--------------------------|:--------------------------|
| deployed (retrained) |    0.7193 |       0.1087 |     0.7076 |        0.1501 |           0.0577 |                    109 | 1.9% (worst -0.20)       | 3.2% (worst -0.29)        | 6.1% (worst -0.32)        |
| monotone             |    0.7146 |       0.1048 |     0.6949 |        0.1351 |           0.0577 |                     40 | 0.0% (worst +0.00)       | 0.0% (worst +0.00)        | 0.0% (worst +0.00)        |

Reproduces the deployed model (test ROC-AUC 0.708 ± 0.005): **True**.

**Decision:** not a v1.0 candidate under the pre-set rule {'no_violations': True, 'test_pr_auc_within_0.01': False, 'val_pr_auc_within_0.01': True}.
