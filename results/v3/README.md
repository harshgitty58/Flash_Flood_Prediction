# results/v3: v1.0 research studies (PRAHAR_MASTER_PLAN.md)

Each study's adoption rule is written in its module docstring **before** it was run. None of them changes the deployed app; adopted candidates wait for the multi-year protocol (ADR-007).

| File | Question | Answer (2026-10-21) |
|---|---|---|
| `rq4_calibration.md` / `.json` (`python -m src.calibration_study`) | Which calibrator for the deployed scores? | **Platt / beta pass the rule**: test log-loss 0.199 vs 0.203 (IVAP), ECE 0.013 vs 0.031, 109 distinct values vs 22. Root cause of the coarse probabilities: the model emits only 109 raw scores and 72 % of test hours share one. Candidate for v1.0. |
| `rq8_hysteresis.md` / `.json` (`python -m src.hysteresis_study`) | Does tier hysteresis stop flicker without costing skill? | **Not needed.** The deployed tiers change only 0.41 times per gauge-day. A 6 h hold cuts that to 0.39 (not halved) and turns one early warning into an "already on" baseline. Rejected with evidence. |
| `v38_monotone.md` / `.json` (`python -m src.monotone_study`) | Can "more rain never lowers risk" be enforced for free? | **No.** Monotone constraints remove every violation (3.2 % of hours today, worst −0.29) but test PR-AUC falls 0.150 → 0.135. Not adopted; re-test with the v1.0 data. |
| `terrain_at_gauges.csv` / `.md` (`python scripts/terrain_at_gauges.py`) | The brief's terrain parameters at every gauge from the 30 m Copernicus DEM | 51 / 51 gauges: elevation, slope, aspect, TRI, TWI, SPI, upstream area, HAND, distance to channel, 1 km relief. Matches the earlier DEM: elevation r = 1.000, median difference 4 m. Ready for the v1.0 feature set (WS-04.7). |
