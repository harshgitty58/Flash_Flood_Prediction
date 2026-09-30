# Antigravity Agent Brief — Phase 3
## Objective 3: Optimized Multi-Model Training and Evaluation

> **Project:** Evaluating Multi-Source Data Fusion and Uncertainty in Hyper-Local Flash-Flood Prediction for Hilly Regions of India  
> **Initial region:** Uttarakhand, India  
> **Current phase:** Phase 3 / Objective 3  
> **Status before this phase:** Objective 1 is complete. Objective 2 is the required preprocessing/data-preparation stage and must produce the ML-ready dataset consumed here.
>
> **Primary instruction:** Build, optimize, compare, validate, and document the candidate ML models.  
> **Do not move into uncertainty quantification, robustness experiments, deployment, or the final early-warning system in this phase. Those belong to later work.**

---

# 1. FINALIZED PROJECT OBJECTIVES

These four objectives are fixed and must not be rewritten or replaced.

## Objective 1 — Dataset Curation and Multi-Source Integration

Curate and integrate heterogeneous datasets from **rainfall, soil moisture, river discharge, terrain, flood history, and landslide records** to create a unified, geographically and temporally aligned dataset for Uttarakhand flash-flood prediction.

## Objective 2 — Data Transformation, Cleaning and Normalization

Perform **data cleaning, missing-value handling, outlier detection, normalization, feature transformation, spatial-temporal alignment, and feature engineering** to convert raw multi-source data into a consistent ML-ready dataset.

## Objective 3 — Optimized Multi-Model Training and Evaluation

Develop and compare multiple ML models such as **Logistic Regression, Random Forest, and XGBoost**, using **optimized training, hyperparameter tuning, efficient feature selection, and rigorous train/test validation** to identify reliable prediction models.

## Objective 4 — Uncertainty-Aware and Robust Flood Prediction

Enhance the selected model with **uncertainty estimation and robustness analysis**, evaluating prediction reliability under **missing, noisy, or degraded observations** and translating the results into practical early-warning levels.

---

# 2. PROJECT CONTEXT

The project is designed as a multi-source, uncertainty-aware flash-flood early-warning framework for hilly regions of India.

The first implementation is **Uttarakhand only**.

The project specification identifies a primary target:

> **Flood event within the next 24 hours**

It also identifies flood severity as a secondary target and identifies flood probability, warning lead time, and prediction uncertainty as system outputs.

Candidate feature families include:

- precipitation/rainfall
- soil moisture
- terrain/topography
- hydrology
- historical flood information
- historical landslide information
- temporal variables
- spatial variables
- optional land-use/land-cover and other variables

The planned model family is:

1. **Logistic Regression** — baseline
2. **Random Forest** — non-linear baseline
3. **XGBoost** — main tabular prediction model
4. **XGBoost + Conformal Prediction** — uncertainty-aware extension for Objective 4
5. **SHAP + selected model** — interpretability layer

This phase concerns **1–3** above. Conformal prediction and the full SHAP/robustness/uncertainty study come later.

---

# 3. WHAT PHASE 3 RECEIVES FROM OBJECTIVE 2

Do not train directly from unprocessed source CSV files.

Phase 3 must consume the outputs of Objective 2.

At minimum, Objective 2 should provide:

```text
final ML-ready dataset
feature dictionary
target definition
train/validation/test time boundaries
preprocessing pipeline
missing-value strategy
outlier strategy
spatial alignment strategy
feature-generation definitions
data-quality report
```

Recommended project structure:

```text
Dataset/
├── curated_dataset/
│   ├── rainfall/
│   ├── river_discharge/
│   ├── flood_inventory/
│   └── landslide_inventory/
│
└── processed/
    ├── cleaned/
    ├── aligned/
    ├── features/
    ├── targets/
    └── final/
```

The preferred modelling input is the final Objective 2 output, for example:

```text
Dataset/processed/final/
    uttarakhand_flash_flood_ml_dataset.parquet
```

and optionally:

```text
Dataset/processed/final/
    uttarakhand_flash_flood_ml_dataset.csv
```

---

# 4. CORE TASK FOR PHASE 3

Build a reproducible supervised-learning pipeline:

```text
Objective 2 ML-ready dataset
        ↓
Target verification
        ↓
Feature/target separation
        ↓
Chronological train/validation/test split
        ↓
Baseline preprocessing
        ↓
Baseline Logistic Regression
        ↓
Random Forest
        ↓
XGBoost
        ↓
Hyperparameter tuning
        ↓
Feature selection / ablation
        ↓
Validation
        ↓
Final untouched test evaluation
        ↓
Model comparison report
        ↓
Persist trained model + preprocessing
```

The central question for this phase is:

> How do Logistic Regression, Random Forest, and XGBoost perform when trained and validated fairly on the same leakage-free Uttarakhand forecasting problem, and how does optimization/feature selection affect their performance?

---

# 5. PHASE 3 PRINCIPLES

The agent must follow these principles throughout.

## Principle 1 — One task, one target definition

Do not change the target definition between models.

All candidate models must receive the same target.

## Principle 2 — Same evaluation data

All models must be compared on the same validation/test observations.

## Principle 3 — No future information

This is a forecasting problem.

No feature, preprocessing parameter, hyperparameter decision, or model selection decision may use information from the final test period.

## Principle 4 — Preserve an untouched test set

Once the final test period is defined, it must remain untouched until the model-development decisions are finished.

## Principle 5 — Optimize on training/validation only

Hyperparameter tuning must never optimize directly on the final test set.

## Principle 6 — Document every decision

Record:

- split dates
- preprocessing
- features used
- hyperparameter search space
- selected hyperparameters
- random seeds
- metrics
- threshold selection rule
- feature-selection rule
- model version
- software/library versions where practical

## Principle 7 — Do not assume statistical outliers are bad observations

A genuine extreme rainfall/discharge event can be exactly the event the model needs to learn.

Objective 2 is responsible for data quality decisions; Phase 3 should not silently rewrite the data.

---

# 6. TASK DEFINITION

## 6.1 Primary task — Binary flood-event classification

The required primary target is:

```text
Flood event within next 24 hours
```

Represent as:

```text
target_flood_24h ∈ {0, 1}
```

where:

```text
1 = relevant flood event begins within the defined next-24-hour forecast horizon
0 = otherwise
```

The exact target construction must come from Objective 2.

Do not invent a new flood-labeling rule in this phase.

## 6.2 Secondary target — Flood severity

Flood severity is part of the original project design.

However, only implement a severity-prediction task if Objective 2 produced a defensible secondary target with sufficient data quality and a clear definition.

Do not force a severity model simply because the specification mentions it.

If severity is not ready:

```text
document:
"Secondary severity modelling deferred until the target is sufficiently validated."
```

The mandatory Phase 3 task is the binary 24-hour event prediction.

---

# 7. INPUT FEATURES

The specification identifies numerous candidate feature families.

Use only features actually available in the final Objective 2 dataset.

Potential families include:

## Rainfall

- rainfall_1h
- rainfall_3h
- rainfall_6h
- rainfall_12h
- rainfall_24h
- rainfall_48h
- rainfall_72h
- maximum rainfall intensity
- rainfall intensity change
- Antecedent Precipitation Index
- hours since rainfall started
- hours since heavy rainfall started

## Hydrology

- river discharge
- discharge change 1h
- discharge change 3h
- discharge change 6h
- rolling mean discharge
- rolling maximum discharge
- discharge anomaly

## Historical flood information

Where valid:

- historical flood count
- flood frequency 5y
- flood frequency 10y
- days since last flood
- historical flood severity
- historical flooded area
- District Flood Severity Index
- historical flood hotspot

## Historical landslide information

Where valid:

- historical landslide count
- landslide density
- distance to nearest historical landslide
- historical landslide hotspot
- landslide-prone indicator

## Temporal

- hour
- day of week
- day of year
- month
- season
- monsoon indicator
- monsoon phase

## Spatial

- latitude
- longitude
- station ID
- district
- catchment/watershed ID if available
- elevation zone if available

## Other features

Only use soil moisture, terrain, LULC, etc. if actually available in the Objective 2 final dataset.

**Never create fake values for unavailable data.**

---

# 8. FEATURE GROUP EXPERIMENT DESIGN

A major purpose of the project is multi-source data fusion.

Therefore do not only train one model with every feature.

Create controlled feature-group experiments.

At minimum, evaluate:

### Experiment A — Rainfall only

```text
Rainfall features
```

### Experiment B — Rainfall + discharge

```text
Rainfall
+
Hydrology
```

### Experiment C — Add historical flood information

```text
Rainfall
+
Hydrology
+
Historical flood
```

### Experiment D — Add landslide information

```text
Rainfall
+
Hydrology
+
Historical flood
+
Historical landslide
```

### Experiment E — Full available feature set

```text
all valid Objective 2 features
```

If additional feature families are available, add them as separate controlled groups.

The purpose is to quantify the incremental contribution of the additional information sources.

Do not change multiple unrelated things between experiments.

---

# 9. PREPROCESSING FOR MODEL TRAINING

Preprocessing must be fitted using training data only.

General flow:

```text
Train period
   ↓
fit imputation/scaling/encoding
   ↓
Validation/test transformed using fitted objects
```

Never do:

```text
fit preprocessing on all rows
split afterwards
```

That leaks information.

---

# 10. LOGISTIC REGRESSION

Logistic Regression is the interpretable baseline.

It establishes a simple probabilistic reference.

## Required characteristics

- binary classifier
- probability output required
- numeric features
- scaling where appropriate
- categorical variables encoded only if they are included
- regularization

Potential hyperparameters:

```text
C
penalty
solver
class_weight
```

Do not blindly search incompatible parameter combinations.

## Required outputs

- predicted class
- predicted probability
- validation metrics
- test metrics
- selected hyperparameters
- coefficient table

Coefficient tables should be exported for interpretability.

---

# 11. RANDOM FOREST

Random Forest is the non-linear baseline.

It is intended to capture interactions and non-linear relationships with limited preprocessing assumptions.

Potential hyperparameters:

```text
n_estimators
max_depth
min_samples_split
min_samples_leaf
max_features
class_weight
```

Use a reproducible random seed.

Consider controlling computational cost:

```text
n_jobs = -1
```

when appropriate.

## Required outputs

- predicted class
- predicted probability
- validation metrics
- test metrics
- selected hyperparameters
- feature importance table

Do not treat built-in impurity feature importance as the final explanation of causal influence.

Interpretability is addressed more fully later.

---

# 12. XGBOOST

XGBoost is the main tabular model in the project design.

Potential hyperparameters include:

```text
n_estimators
max_depth
learning_rate
subsample
colsample_bytree
min_child_weight
gamma
reg_alpha
reg_lambda
```

The agent must choose a computationally realistic search space.

Do not perform a huge brute-force grid search unnecessarily.

Prefer:

```text
RandomizedSearchCV
```

or another efficient search strategy, or a controlled parameter search.

If class imbalance is substantial, investigate an appropriate training-only imbalance strategy such as `scale_pos_weight`.

Do not determine class imbalance parameters using the test set.

---

# 13. CLASS IMBALANCE

Flood events may be much less frequent than non-flood observations.

The agent must explicitly measure:

```text
positive class count
negative class count
positive class percentage
```

on each split.

Do not rely on raw accuracy as the main metric under imbalance.

Potential approaches:

### Logistic Regression

```text
class_weight="balanced"
```

or a documented custom class weighting strategy.

### Random Forest

```text
class_weight="balanced"
```

or documented alternative.

### XGBoost

Potentially:

```text
scale_pos_weight
```

computed from the training set only.

The agent should compare whether imbalance handling actually improves validation performance rather than assuming it always does.

---

# 14. TRAIN / VALIDATION / TEST STRATEGY

Because the problem is forecasting over time, use **chronological splitting**.

Do not use a random row-wise split as the only evaluation method.

Recommended conceptual structure:

```text
earlier dates
───────────────
TRAIN
───────────────
VALIDATION
───────────────
TEST
───────────────
later dates
```

The exact dates must be determined from the final Objective 2 dataset and documented.

The test set must represent future observations relative to training.

---

# 15. TIME-SERIES VALIDATION FOR HYPERPARAMETER TUNING

Where computationally feasible, use time-aware cross-validation inside the training/development period.

For example:

```text
Fold 1:
train early period → validate next period

Fold 2:
train larger earlier period → validate following period

Fold 3:
train larger earlier period → validate following period
```

Avoid standard shuffled K-fold for a forecasting problem unless a separate experiment explicitly justifies it.

The final test period remains untouched.

---

# 16. HYPERPARAMETER TUNING

Hyperparameter tuning belongs inside the training/development workflow.

General process:

```text
Training data
    ↓
time-aware CV
    ↓
hyperparameter search
    ↓
best configuration selected using validation/CV
    ↓
fit optimized model
    ↓
evaluate once on untouched test
```

Never do:

```text
test set
 ↓
try many hyperparameters
 ↓
keep whichever scores highest
```

That creates test-set overfitting.

---

# 17. SCORING FOR MODEL OPTIMIZATION

Use multiple metrics.

At minimum calculate:

### ROC-AUC

Measures ranking quality over thresholds.

### PR-AUC / Average Precision

Important when flood events are relatively rare.

### Precision

Of predicted flood events, how many were actually events?

### Recall / Sensitivity

Of actual flood events, how many were detected?

### F1 score

Harmonic mean of precision and recall.

### Specificity

Ability to correctly identify non-flood observations.

### Balanced Accuracy

Useful when classes are imbalanced.

### MCC

Useful as an additional robust classification metric under imbalance.

### Brier Score

Useful for evaluating probability quality.

### Log Loss

Evaluates probabilistic predictions.

Do not report only accuracy.

---

# 18. PROBABILITY CALIBRATION

Because the final project intends to produce flood probabilities, probability quality matters.

For each model, where supported, evaluate:

```text
predicted probability
vs
observed event frequency
```

Use a calibration curve.

Report:

- Brier score
- calibration plot
- reliability diagram
- optionally calibration error summaries

Do not recalibrate using the final test set.

Calibration must be developed using the training/development data.

---

# 19. THRESHOLD HANDLING

Do not assume the final operational threshold is always 0.5.

Evaluate the classification threshold separately from the probability model.

Recommended:

1. Establish a baseline threshold of 0.50.
2. Evaluate threshold-dependent metrics.
3. Select an alternative threshold using training/validation data only if the research experiment requires it.
4. Freeze the selected threshold before final test evaluation.
5. Report both probability performance and threshold-based classification performance.

Possible threshold analysis:

```text
0.10
0.20
0.30
...
0.90
```

But the threshold grid should be an evaluation tool, not a mechanism for cherry-picking the test result.

Threshold trade-offs are important because the later project stage will study false alarms versus missed floods.

---

# 20. FEATURE SELECTION

Objective 3 explicitly requires efficient feature selection.

Feature selection must be performed without test leakage.

Possible approaches:

## A. Correlation/redundancy filtering

Identify highly redundant numeric features.

Do this based on training data.

Do not automatically drop variables solely because they correlate with another unless redundancy is confirmed and the decision is justified.

## B. Model-based selection

Examples:

- logistic regression coefficients
- Random Forest importance
- XGBoost importance

Use training/development data.

## C. Permutation importance

Use validation/development data rather than final test data for feature-selection decisions.

## D. Recursive feature elimination

Use only if computationally reasonable.

## Important rule

Feature selection must not use information from the final test period.

---

# 21. FEATURE ABLATION

Feature ablation is strongly recommended.

For example:

```text
Full model
Full minus rainfall
Full minus discharge
Full minus historical flood
Full minus landslide
```

Do not remove features randomly.

The purpose is to quantify how model performance changes when a data source is removed.

This connects directly to the project's multi-source data-fusion objective.

---

# 22. MODEL COMPARISON TABLE

Generate a single machine-readable comparison table.

Recommended columns:

```text
model
feature_set
cv_roc_auc
cv_pr_auc
validation_roc_auc
validation_pr_auc
validation_precision
validation_recall
validation_f1
validation_specificity
validation_balanced_accuracy
validation_mcc
validation_brier
validation_log_loss
test_roc_auc
test_pr_auc
test_precision
test_recall
test_f1
test_specificity
test_balanced_accuracy
test_mcc
test_brier
test_log_loss
threshold
training_time_seconds
inference_time_seconds
```

If a metric is not appropriate or unavailable, document it rather than inserting an arbitrary value.

---

# 23. VISUALIZATIONS

Create reproducible plots for each model.

At minimum:

### Confusion matrix

For the selected operating threshold.

### ROC curve

Compare models on the same test set.

### Precision-Recall curve

Especially important for imbalance.

### Calibration curve

Compare predicted probabilities with observed outcomes.

### Feature importance

For Random Forest/XGBoost where appropriate.

### Hyperparameter-search summary

Show how performance changed across the selected search space where useful.

### Model comparison chart

Show major metrics side-by-side without hiding the underlying numerical results.

Save plots to:

```text
results/model_evaluation/
```

Recommended naming:

```text
logistic_regression_roc.png
random_forest_roc.png
xgboost_roc.png

logistic_regression_pr.png
random_forest_pr.png
xgboost_pr.png

model_calibration.png
model_comparison.csv
model_comparison.png
```

---

# 24. CROSS-VALIDATION OUTPUTS

Save the CV results.

Recommended:

```text
results/model_evaluation/
    logistic_regression_cv_results.csv
    random_forest_cv_results.csv
    xgboost_cv_results.csv
```

Each should record:

- split/fold identifier
- training period
- validation period
- selected metric(s)
- hyperparameters
- score

This allows the training process to be audited.

---

# 25. HYPERPARAMETER SEARCH RECORD

For every optimized model, save:

```text
results/hyperparameter_tuning/
    logistic_regression_search.csv
    random_forest_search.csv
    xgboost_search.csv
```

Also save a compact JSON/YAML representation of the selected configuration:

```text
results/hyperparameter_tuning/
    logistic_regression_best_params.json
    random_forest_best_params.json
    xgboost_best_params.json
```

Do not save only the final parameters without the search results.

---

# 26. MODEL ARTIFACTS

Persist the trained models.

Recommended:

```text
models/
├── logistic_regression/
│   ├── model.joblib
│   └── metadata.json
│
├── random_forest/
│   ├── model.joblib
│   └── metadata.json
│
└── xgboost/
    ├── model.joblib
    └── metadata.json
```

Metadata should include:

```text
model type
feature set
target
training date
training data range
software/library version
selected hyperparameters
random seed
preprocessing reference
threshold
validation strategy
```

Do not store hidden or undocumented assumptions inside the model file.

---

# 27. PREDICTION ARTIFACTS

Save out-of-sample predictions.

For validation:

```text
results/predictions/
    validation_logistic_regression.csv
    validation_random_forest.csv
    validation_xgboost.csv
```

For the final test:

```text
results/predictions/
    test_logistic_regression.csv
    test_random_forest.csv
    test_xgboost.csv
```

Recommended fields:

```text
station
datetime
district
target
predicted_probability
predicted_class
model
feature_set
```

These predictions are important for later calibration, threshold analysis, uncertainty work, and error analysis.

---

# 28. ERROR ANALYSIS

Do not stop at a metric table.

Create an error analysis for the models.

Inspect:

### False positives

Cases where:

```text
actual = 0
prediction = 1
```

### False negatives

Cases where:

```text
actual = 1
prediction = 0
```

For each category, investigate:

- rainfall conditions
- discharge conditions
- station/district
- season
- historical hazard context
- whether observations were missing or degraded
- whether the event definition may contribute to ambiguity

Do not manually alter labels to make errors disappear.

---

# 29. RARE-EVENT CHECK

Explicitly report:

```text
number of flood positives
number of non-flood negatives
positive rate
```

for:

- entire dataset
- train
- validation
- test

This guards against accidental class-distribution shifts.

If a chronological split produces a test period with no positive events, document the limitation rather than claiming model performance is fully established.

---

# 30. TEMPORAL STABILITY

The model should not be evaluated only as one single number.

Where the data volume allows, calculate performance by:

- year
- season
- monsoon/non-monsoon
- district
- station

This is not yet the full spatial-generalization experiment.

It is a diagnostic to identify instability.

Save:

```text
results/model_evaluation/
    performance_by_year.csv
    performance_by_district.csv
    performance_by_station.csv
    performance_by_season.csv
```

---

# 31. RANDOM SEEDS AND REPRODUCIBILITY

Use explicit random seeds where the algorithm/search process is stochastic.

Record the seed in metadata.

For example:

```text
random_state = 42
```

is acceptable unless the project establishes another seed.

The important requirement is **reproducibility**, not a particular seed number.

Where practical, run more than one seed as a sensitivity check.

Do not report only the most favorable random seed.

---

# 32. EFFICIENT COMPUTATION

The dataset is time-series tabular data, not image data.

Prioritize:

- vectorized preprocessing
- efficient feature selection
- time-aware CV
- randomized or bounded hyperparameter search
- parallel CPU training where appropriate
- reuse of transformed datasets

Avoid:

- unnecessary brute-force combinations
- repeated parsing of raw files
- duplicating huge DataFrames in memory
- tuning on the test set

Log runtime where practical.

---

# 33. CODE ORGANIZATION

Do not create one enormous training notebook.

Recommended source structure:

```text
src/
├── config.py
├── data_loader.py
├── split.py
├── preprocessing.py
├── imbalance.py
├── feature_selection.py
├── train_logistic.py
├── train_random_forest.py
├── train_xgboost.py
├── tune_models.py
├── evaluate.py
├── calibration.py
├── threshold.py
└── model_registry.py
```

Recommended notebooks:

```text
notebooks/
├── 05_baseline_models.ipynb
├── 06_hyperparameter_tuning.ipynb
├── 07_feature_selection_and_ablation.ipynb
└── 08_model_evaluation.ipynb
```

Notebooks should demonstrate the experiments.

Reusable implementation should live in `src/`.

---

# 34. CONFIGURATION

Create a central configuration rather than hard-coding parameters throughout notebooks.

For example:

```text
configs/
    phase3_training.yaml
```

This should define:

```yaml
target:
  name: target_flood_24h

split:
  strategy: chronological

models:
  logistic_regression: true
  random_forest: true
  xgboost: true

evaluation:
  metrics:
    - roc_auc
    - pr_auc
    - precision
    - recall
    - f1
    - balanced_accuracy
    - mcc
    - brier
    - log_loss

random_seed: 42
```

Do not hard-code contradictory settings elsewhere.

---

# 35. MODEL REGISTRY

Create a lightweight model registry.

Example:

```text
results/model_registry.csv
```

Recommended fields:

```text
model_id
model_name
version
feature_set
target
train_start
train_end
validation_start
validation_end
test_start
test_end
hyperparameter_file
model_file
metrics_file
threshold
notes
```

This will make later selection and deployment easier.

---

# 36. FAIR MODEL COMPARISON

All three primary models must be compared fairly.

The following should remain constant where possible:

- target
- train period
- validation period
- test period
- feature set
- evaluation observations
- leakage rules

Model-specific preprocessing is allowed when mathematically appropriate.

Example:

```text
Logistic Regression → scaling may be used
Random Forest → scaling is generally unnecessary
XGBoost → scaling is generally unnecessary
```

Do not deliberately cripple one model by applying inappropriate preprocessing.

---

# 37. MODEL SELECTION FOR LATER OBJECTIVE 4

At the end of Phase 3, identify the model/configuration that will be carried into Objective 4.

The selection must be based on **predefined, documented criteria** rather than a subjective choice made after seeing many test results.

Possible considerations:

- PR-AUC
- recall
- precision
- F1
- MCC
- probability calibration
- stability across validation folds
- computational cost
- operational interpretation

The selected candidate is then passed to Phase 4 for:

```text
uncertainty estimation
robustness analysis
observation degradation
warning-level analysis
```

Do not apply conformal prediction to the test set in this phase.

---

# 38. IMPORTANT: TEST SET DISCIPLINE

The final test set is for final confirmation.

The agent must not:

- tune hyperparameters on test
- select features on test
- select the threshold on test
- choose the feature group solely by test performance
- compare dozens of approaches and then report only the best test score
- repeatedly inspect the test set and iterate

Correct workflow:

```text
TRAIN
  ↓
CV / DEVELOPMENT
  ↓
hyperparameter selection
  ↓
feature selection
  ↓
threshold selection
  ↓
freeze model
  ↓
ONE FINAL TEST EVALUATION
```

---

# 39. DATA LEAKAGE CHECKLIST

Before reporting Phase 3 results, explicitly verify:

- [ ] No future timestamps entered training features.
- [ ] Rolling features are backward-looking.
- [ ] Historical flood counts exclude future events.
- [ ] Historical landslide features exclude future events where time-dependent.
- [ ] Scalers were fitted only on training data.
- [ ] Encoders were fitted only on training data.
- [ ] Imputers were fitted only on training/development data.
- [ ] Feature selection did not use final test data.
- [ ] Hyperparameter tuning did not use final test data.
- [ ] Threshold selection did not use final test data.
- [ ] Calibration did not use final test data.
- [ ] Test performance was evaluated only after model decisions were frozen.

Create:

```text
results/model_evaluation/leakage_audit.md
```

---

# 40. PERFORMANCE REPORT

Create:

```text
results/model_evaluation/phase3_model_report.md
```

The report should contain:

## 1. Objective

What Phase 3 was designed to accomplish.

## 2. Dataset

- source dataset
- number of observations
- features
- target
- temporal coverage

## 3. Split

- training dates
- validation dates
- test dates
- number of observations in each

## 4. Class balance

- positive/negative counts
- positive rate

## 5. Models

- Logistic Regression
- Random Forest
- XGBoost

## 6. Tuning

- search method
- search space
- selected parameters

## 7. Feature selection

- features removed
- features retained
- selection method

## 8. Feature-group experiments

- rainfall-only
- rainfall+discharge
- historical flood addition
- landslide addition
- full available feature set

## 9. Validation results

Full metric table.

## 10. Final test results

Full metric table.

## 11. Calibration

Brier/log loss + reliability plots.

## 12. Error analysis

False positives and false negatives.

## 13. Stability

Results by year/season/district/station where data support it.

## 14. Limitations

Clearly state dataset limitations.

## 15. Candidate model for Objective 4

Document which trained candidate is being carried forward and why, based on the predefined criteria.

---

# 41. MINIMUM REQUIRED DELIVERABLES

Phase 3 is not complete unless the following exist:

```text
results/
├── model_evaluation/
│   ├── phase3_model_report.md
│   ├── model_comparison.csv
│   ├── model_comparison.png
│   ├── leakage_audit.md
│   ├── performance_by_year.csv
│   ├── performance_by_district.csv
│   └── performance_by_season.csv
│
├── hyperparameter_tuning/
│   ├── logistic_regression_search.csv
│   ├── random_forest_search.csv
│   ├── xgboost_search.csv
│   ├── logistic_regression_best_params.json
│   ├── random_forest_best_params.json
│   └── xgboost_best_params.json
│
└── predictions/
    ├── validation_logistic_regression.csv
    ├── validation_random_forest.csv
    ├── validation_xgboost.csv
    ├── test_logistic_regression.csv
    ├── test_random_forest.csv
    └── test_xgboost.csv
```

And:

```text
models/
├── logistic_regression/
├── random_forest/
└── xgboost/
```

---

# 42. OPTIONAL BUT STRONGLY RECOMMENDED DELIVERABLES

Also create:

```text
results/
├── feature_selection/
│   ├── selected_features.csv
│   ├── removed_features.csv
│   └── feature_ablation_results.csv
│
└── plots/
    ├── roc_curves.png
    ├── precision_recall_curves.png
    ├── calibration_curves.png
    ├── confusion_matrices.png
    └── feature_importance.png
```

---

# 43. DO NOT START OBJECTIVE 4 YET

Phase 3 must stop before:

- conformal prediction
- prediction intervals / conformal sets
- observation degradation experiments
- simulated sensor outages
- explicit noise-injection robustness experiments
- uncertainty reliability analysis
- final warning-level design
- deployment dashboard/API
- cross-region generalization to Sikkim/Himachal Pradesh

These belong to later stages.

Phase 3 prepares the selected model and clean evaluation artifacts needed for those experiments.

---

# 44. DO NOT FABRICATE RESULTS

The agent must never:

- invent metrics
- assume XGBoost is strongest without testing
- invent a feature importance ranking
- claim a feature improved performance without an experiment
- claim generalization without a holdout experiment
- claim operational readiness from offline test results alone

All conclusions must come from saved experimental outputs.

---

# 45. FINAL PHASE 3 DEFINITION OF DONE

Objective 3 is complete when:

```text
Objective 2 ML-ready dataset
        ↓
target verified
        ↓
chronological train/validation/test split
        ↓
Logistic Regression baseline
        ↓
Random Forest baseline
        ↓
XGBoost baseline
        ↓
hyperparameter tuning
        ↓
feature selection
        ↓
multi-source feature-group experiments
        ↓
time-aware validation
        ↓
probability evaluation/calibration
        ↓
threshold analysis
        ↓
final untouched test evaluation
        ↓
error analysis
        ↓
model comparison report
        ↓
trained model artifacts
        ↓
prediction artifacts
        ↓
leakage audit
        ↓
candidate model documented for Objective 4
```

At this point, Objective 3 can be marked complete.

---

# 46. HANDOFF TO OBJECTIVE 4

The handoff from Phase 3 must contain:

```text
selected candidate model
model artifact
preprocessing artifact
feature list
target definition
train/validation/test periods
selected threshold
validation metrics
test metrics
calibration results
prediction files
model metadata
feature-ablation results
leakage audit
phase3_model_report.md
```

Objective 4 will then use this frozen modelling setup to investigate:

```text
missing observations
sensor outages
measurement noise
observation degradation
uncertainty estimation
Conformal Prediction
warning-level interpretation
```

---

# 47. FINAL AGENT INSTRUCTION

Treat this document as the **master implementation specification for Phase 3 / Objective 3**.

The implementation should prioritize:

```text
scientific validity
↓
no leakage
↓
reproducibility
↓
fair model comparison
↓
efficient optimization
↓
clear documentation
```

Do not optimize for an attractive single test score.

The objective is to build a defensible, reproducible comparison of Logistic Regression, Random Forest, and XGBoost for the Uttarakhand 24-hour flood-event prediction task, with the resulting candidate model ready for the uncertainty and robustness experiments in Objective 4.

---

# Source Alignment

The project specification defines the initial region as Uttarakhand and describes a multi-source flood prediction problem combining precipitation, soil moisture, terrain, hydrological conditions, and historical flood/landslide information. It defines **flood event within the next 24 hours** as the primary target. The planned model sequence identifies Logistic Regression as the baseline, Random Forest as the non-linear baseline, and XGBoost as the main prediction model; uncertainty-aware XGBoost with conformal prediction is reserved for the later uncertainty stage.

This Phase 3 document expands those project requirements into a reproducible training and evaluation workflow without changing the finalized four objectives.
