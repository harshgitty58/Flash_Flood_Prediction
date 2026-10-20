# Architecture decision records

Format: Context → Decision → Consequences → Status. The full reasoning for planned decisions is in `PRAHAR_MASTER_PLAN.md` Appendix E. Decisions already taken are recorded here.

| ADR | Decision | Status |
|---|---|---|
| 001 | New repository (`harshgitty58/Flash_Flood_Prediction`); the old repositories are left untouched as archives | accepted 2026-10-21 |
| 002 | Hackathon Track B (Space mode) moved out of the course project into a separate archive folder | accepted 2026-10-20 |
| 003 | Two-tier intelligence: PREPARE (district-day, 2001–2025 gridded data) + NOWCAST (gauge-hour) | proposed (v1.0) |
| 004 | Store UTC, display IST | proposed (v1.0) |
| 005 | Coverage mask: "no report ≠ no flood"; negatives only where a high-recall source was monitoring | accepted for labels v1 (label end 2023-08-26); generalised in v3 |
| 006 | XGBoost uses native NaN (no median imputation) so sensor outages stay visible | proposed (v1.0) |
| 007 | Model selection rule, fixed before tuning: [ADR-007](ADR-007-model-selection.md) | accepted 2026-10-21 |
| 008 | Calibrator chosen by RQ4. Platt / beta pass the pre-set rule on the test month (`results/v3/rq4_calibration.md`); the switch waits for the multi-year protocol | candidate |
| 009 | Tier hysteresis: not adopted. The deployed tiers already change < 0.5 times per gauge-day (`results/v3/rq8_hysteresis.md`) | rejected with evidence 2026-10-21 |
| 010 | Official river-setback zones (50 / 100 / 200 m) are the legal frame for exposure; a probability-aware score sits beside them | accepted (zones); score proposed |
| 011 | PostgreSQL + PostGIS + TimescaleDB for the operational store | proposed (v1.0) |
| 013 | PMTiles for the building layer | proposed (v1.0) |
| 015 | Static JSON demo mode is kept alongside the API | accepted |
| 016 | Any CAP alert feed carries `status=Exercise` until an authority signs off | accepted |
| 017 | Latitude and longitude excluded as model features (location leakage, A2) | accepted |
| 018 | No resampling (SMOTE etc.); class weights + calibration | accepted |
| 019 | Monotone rain constraints: not adopted for now. They remove all rain-lowers-risk cases but cost 0.015 test PR-AUC (`results/v3/v38_monotone.md`); re-test with the v1.0 data | rejected with evidence 2026-10-21 |
| 020 | One district-day definition for headlines: strict WMO (flood starts on day D); lenient numbers carry their label (`docs/metrics.md`) | accepted 2026-10-21 |
