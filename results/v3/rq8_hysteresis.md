# RQ8 / WS-09.6: warning-tier hysteresis

Escalate immediately; drop one level only after N calm hours. Scored with the published strict district-day verification (validation + test pooled, ≥ ALERT). Rule fixed before the run: see `src/hysteresis_study.py`.

| rule                     |   flicker / gauge-day (Jul-Aug 2023) |   flicker / gauge-day (replay) |   dd POD |   dd FAR |   dd CSI |   ALERT district-days | warned before / baseline / missed   |
|:-------------------------|-------------------------------------:|-------------------------------:|---------:|---------:|---------:|----------------------:|:------------------------------------|
| deployed (no hysteresis) |                                0.412 |                          0.177 |    0.667 |    0.953 |    0.046 |                   255 | 6 / 7 / 5                           |
| hold_3h                  |                                0.417 |                          0.19  |    0.722 |    0.951 |    0.049 |                   263 | 6 / 7 / 5                           |
| hold_6h                  |                                0.387 |                          0.18  |    0.722 |    0.952 |    0.047 |                   271 | 5 / 8 / 5                           |
| hold_12h                 |                                0.35  |                          0.162 |    0.722 |    0.954 |    0.045 |                   281 | 4 / 10 / 4                          |

**Decision (6 h):** not adopted {'flicker_halved': False, 'csi_within_0.01': True, 'pod_within_0.05': True}.

**Reading:** the deployed tiers already change less than once per gauge-day (the plan's target is <= 1.0), so there is little flicker to remove. Stepping down one level at a time can even add changes (EXTREME to NORMAL becomes three steps), and longer holds add ALERT district-days and turn some early warnings into 'already on' baselines. Hysteresis is therefore not needed for the current tiers; WS-09.6 is closed with this evidence and re-checked when the v1.0 tiers change.
