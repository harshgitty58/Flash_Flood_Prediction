# Conformal / Venn-Abers coverage report

Calibration: validation set (20280 rows, 864 positives). Test: 12469 rows, 720 positives.

|   nominal |   coverage_all |   coverage_flood |   coverage_no_flood |   share_uncertain |   share_flood_singleton |
|----------:|---------------:|-----------------:|--------------------:|------------------:|------------------------:|
|      0.8  |         0.8841 |                1 |              0.877  |            0.8508 |                  0.1492 |
|      0.9  |         0.8841 |                1 |              0.877  |            0.851  |                  0.149  |
|      0.95 |         0.9726 |                1 |              0.9709 |            0.9658 |                  0.0342 |

Mean Venn-Abers interval width on test: 0.0006. Brier raw 0.09282 → calibrated 0.05179.

Caveat: with ~20 positives per split, class-1 coverage is estimated on very few points.