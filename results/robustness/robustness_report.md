# Robustness report (inference-time degradation)

Evaluated on 32,749 labelled held-out rows (1584 floods). Missing inputs → training-median imputation.

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

Most damaging scenario: **R3c flood-history records unavailable** (ROC-AUC 0.7155 → 0.5).