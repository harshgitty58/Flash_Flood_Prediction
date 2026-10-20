# Metric definitions

One definition per metric (WS-06.7 and V-37 of `PRAHAR_MASTER_PLAN.md`). Whenever a number is quoted, it states which definition it uses.

## Units of evaluation
- **Station-hour:** every reporting gauge-hour, with target `flood_event_24h` = a flood recorded in the gauge's district on that calendar day or the next. This is the unit the model is trained on.
- **District-day, strict (headline):** for each district and day D, the warning is the highest tier of the district's gauges from D−1 00:00 to D 23:59. The observation is a flood **starting** on day D (IMD inventory). Source: `src/verification.py`. This is how warnings are issued and judged.
- **District-day, lenient ("training-target day"):** per calendar day, against the training target (flood on D or D+1). Used in `src/tier_tuning.py` and `src/label_experiment.py`. Quote it only with this label.

| Same warnings, Aug 2023 test, hybrid ≥ ALERT | CSI | POD | FAR |
|---|---|---|---|
| strict (headline) | **0.095** [0.034–0.165] | 0.70 | 0.90 |
| lenient | 0.169 [0.091–0.253] | 0.63 | 0.81 |
| baselines (strict): district prior / persistence | 0.036 / 0.053 | | |

## Contingency scores
With a = hits, b = false alarms, c = misses, d = correct negatives:
- POD = a/(a+c)
- FAR = b/(a+b)
- POFD = b/(b+d)
- CSI = a/(a+b+c)
- ETS = (a−a_r)/(a+b+c−a_r), with a_r = (a+b)(a+c)/n
- HSS = 2(ad−bc)/[(a+c)(c+d)+(a+b)(b+d)]
- bias = (a+b)/(a+c)

95 % confidence intervals come from a block bootstrap over days (1,000 resamples).

## Ranking and probability
- **PR-AUC** is always printed with its **base rate**. Lift = PR-AUC ÷ base rate, so 1× is chance. Base rates differ by table (validation 0.043, test 0.058, event-CV 0.081, district-day test 0.068), so PR-AUCs from different tables are not comparable.
- **Brier Skill Score:** 1 − BS/BS_climatology. The climatology is the training base rate for each calendar month.
- **ECE:** Σ (n_k/N)·|observed_k − predicted_k| over 10 equal-mass bins.

## Lead time (one definition)
**Lead time** = the start of the event day minus the first time the district's tier reached ≥ ALERT **and stayed there for at least 3 consecutive hours**, within a 48 h look-back.
- An alert that was already on for most of the 24 h before the look-back opened counts as **"already on (district baseline)"**, not as a lead.
- Current result (Jul–Aug 2023): **6 of 18** events warned before the event day, **median 3.5 h**; 7 already on; 5 missed. Source: `results/verification/verification.json`.
- Retired: the earlier event-CV figure of "36 h at a 5 % hourly false-alarm rate" used a raw-score threshold and an "already on" alarm counted as lead.
- On the external-validation table, "48 h" means the alert was already on when the 48 h window opened.

## Operating points
- Alerts are judged at the **tier cut-offs** only. The cut-offs are calibrated probability ≥ 2× / 5× / 10× / 20× the base rate (0.0852 / 0.2130 / 0.4260 / 0.8521), combined with the IMD rainfall rule.
- The raw-score thresholds on the Metrics page's slider are exploration, not the warning rule: LR 0.85, RF 0.45, XGBoost 0.25, each the max-F1 point on validation.

## Conformal sets
- Mondrian (class-conditional) sets at 80 / 90 / 95 %.
- The set is `{FLOOD}`, `{NO FLOOD}` or both (UNCERTAIN).
- Coverage is reported for each class, together with the share of decisive (single-class) sets.
