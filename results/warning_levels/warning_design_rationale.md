# Warning-level design rationale (hybrid)

Objective 4D — Operational warning tiers (hybrid).

Final tier = max(ML tier, rainfall tier); the layer that set it is recorded in `trigger`.

ML tier — Venn-Abers calibrated probability (src/conformal.py); cut-offs = 2× / 5× / 10× / 20× the calibration base rate.
A conformal FLOOD singleton at 90 % lifts the ML tier to at least ALERT.

Rainfall tier — IMD rainfall categories on the station's own gauge, adjusted for terrain/history susceptibility:
  rain level: moderate rain_24h ≥ 15.6 → 1, heavy ≥ 64.5 → 2, very heavy ≥ 115.6 → 3,
              extremely heavy ≥ 204.5 mm/24 h or cloudburst rain_1h ≥ 100 mm/h → 4
  (the ALERT threshold and a 'fresh rain in the last 6 h' condition are tuned on validation: src/tier_tuning.py)
  susceptibility: +1 if the station is a landslide hotspot AND its district flood-severity index ≥ median,
                  −1 if neither, else 0.  (moderate rain alone never exceeds WATCH)
This layer is a transparent rule, not a learned model: it makes real cloudbursts register even though the
district-date labels cannot teach the rain → flood link (rainfall-only ROC-AUC ≈ 0.5 in event CV).

Base rate (labelled data): 4.26%.

## ≥ ALERT as a classifier (per layer)

|                      |   precision |   recall |    f1 |   false_alarm_rate |   alerts |
|:---------------------|------------:|---------:|------:|-------------------:|---------:|
| validation_tier_ml   |       0.239 |    0.112 | 0.153 |             0.0159 |      406 |
| validation_tier_rain |       0.023 |    0.059 | 0.033 |             0.1124 |     2234 |
| validation_tier      |       0.054 |    0.166 | 0.082 |             0.1283 |     2635 |
| test_tier_ml         |       0.222 |    0.574 | 0.32  |             0.123  |     1858 |
| test_tier_rain       |       0.38  |    0.083 | 0.137 |             0.0083 |      158 |
| test_tier            |       0.234 |    0.65  | 0.344 |             0.1305 |     2001 |

## Tier vs observed

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