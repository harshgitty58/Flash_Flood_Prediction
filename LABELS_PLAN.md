# PRAHAR: Label Curation Plan (2022 – 2025)

**Goal:** turn the label sources we've collected into one auditable event list, `data/external/labels/labels_2022_2025.csv`. The list will be used to:

- check how reliable the IMD training labels are (2022 – Aug 2023);
- extend external validation from 14 events to every documented event, Sep 2023 – 2025;
- decide, with evidence, whether a "label v2" is good enough to retrain on.

**Why:** labels are the bottleneck. The IMD inventory stops on 2023-08-26 and has only 29 district-events since 2022. Every model result, and every claim that a model beats the rainfall baseline, depends on these labels.

---

## 0. Levers that raise the metrics (ranked by expected gain)

Wrong labels hurt twice:
- they **teach the model the wrong thing**: heavy rain on a real flood day labelled "no flood";
- they **score correct alerts as false alarms**.

Every lever below fixes the labels or how they're scored. None of them tunes on the test set.

| # | Lever | What changes | Expected effect | Guardrail |
|---|---|---|---|---|
| **L0** | **Fix the label join (bug).** The IMD inventory writes *Rudra Prayag*, *Udam Singh Nagar* and *Garhwal*; stations use *Rudraprayag*, *Udham Singh Nagar* and *Pauri Garhwal*. *Garhwal* is the Census 2011 name of the Pauri district. | **13 of the 29 IMD event-days in 2022–23 (45 %) are currently lost.** Rudraprayag, the most flood-prone district in the window with 9 event-days, has **0 positives** in training. The same mismatch leaves Pauri stations without DFSI, population and fatality values (they fall back to imputed medians). | Largest single gain. Train and test positives rise by about 45 %. Alerts on real Rudraprayag and Pauri floods stop counting as false alarms, so POD, CSI and precision should rise. | Aliases added in `src/district_mapping.py` and covered by a test. No other change; the before/after is compared on identical splits. |
| L1 | **Label v2.** Add events reported by SANDRP but missing from IMD, 2022–23 | Fills false negatives in the training window | Higher recall; precision measured more honestly | Decision gate in §5; v1 vs v2 compared side by side |
| L2 | **Confidence-weighted training.** `sample_weight` = 1.0 / 0.6 / 0.3 for high / medium / low confidence | Uncertain positives count less | Less noise, better calibration | Weights fixed in advance, not tuned |
| L3 | **Mask uncertain negatives.** Drop from training and scoring: days inside EM-DAT state-wide context windows when the district had ≥ 64.5 mm/24 h, and district-days named only in a vague "affected districts" list | Removes "flood probably happened but went unrecorded" rows | Fewer penalised true alerts, so FAR and CSI improve | Masks are rule-based and decided before evaluation; the masked row count is reported |
| L4 | **Re-derive tier thresholds and recalibrate** after the labels change. The base rate moves, so the 2/5/10/20× multipliers move with it. | Thresholds are refitted on validation only | Keeps tiers meaningful | Test set untouched |
| L5 | **District-day scoring and model** (Phase 4). Labels are district-days, so scoring at that unit stops one district flood being counted as many station-hour hits or misses. | Evaluation unit matches the label unit | Cleaner POD/FAR; enables a calibrated daily probability and district-day BSS | Station-hour metrics kept alongside |
| L6 | **Longer labelled window**: extend to 2023-10-31 if v2 is adopted (SANDRP covers Sep–Oct 2023) | 2 more months, including the end of the monsoon | More data | Only if v2 passes the gate; otherwise stay on IMD's coverage |

**Next levers** (after the label work, ranked by expected gain on the metrics that are still weak):

| # | Lever | Weakness it targets | Plan |
|---|---|---|---|
| L7 | **Fill gauge gaps with USDMA hydromet** (24 state stations, twice-daily) and ERA5 for the rainfall tier | 8 of 29 external events had **no reporting CWC gauge** in the district (e.g. Dehradun on 15 Sep 2025). They score as "no data", and the rainfall rule can't fire. | A district-day rain field takes the max over CWC, hydromet and ERA5 (bias-corrected per station-month on training data). It feeds the rainfall tier only; the ML features stay as they are. Before/after shown on external POD. |
| L8 | **Cut the alert burden**: re-derive the rainfall-tier rules on validation | Hybrid FAR ≈ 0.8–0.9. In 2024 there were 329 ALERT district-days, and only 4 % were near a documented event. | Require ≥ 2 stations, or the persistence used in the lead-time rule (≥ 3 h), before a rainfall-only ALERT. Tune the susceptibility bonus on validation CSI only. Report the POD/FAR trade-off curve. |
| L5 | District-day model (Phase 4) | Station-hour noise; no calibrated daily probability | as above |

**Reporting rule:** every metric is shown as baseline v0 (saved in `results/baseline_v0/`) → after L0 → after each later lever. All use the same splits, event-CV and bootstrap CIs, so each gain can be attributed to a specific change.

---

## Status (2026-10-13)

| Step | Result |
|---|---|
| L0 label-join fix | **Done.** Positives went from 271/384/240 to **367/864/720** (train/val/test). XGBoost on the test month: ROC-AUC 0.535 → **0.708**, PR-AUC 0.036 → **0.150**, F1 0.08 → **0.32**, MCC 0.06 → **0.30**. Event-CV for Exp_G fell from 0.858 to 0.701: the old number was inflated, because positives came from only 5 districts. Event-CV and test now agree. |
| Label set | **Done.** 96 events / 130 district-days from 5 source families; 1 exclusion (lightning only), 0 unresolved. Tests in `tests/test_labels.py`. |
| Audit | **Done.** SANDRP lists **40 events that IMD misses**, against 26 IMD events. The gate passed (154 % ≥ 25 %). |
| v2 experiment | **Done. v2 is not adopted for training** (pre-registered rule). The v2-trained XGBoost is worse on the test month against both truths. As an **answer key**, though, v2 shows the deployed model is better than v1 measures: PR-AUC 0.150 → 0.206, district-day CSI 0.150 → 0.197, FAR 0.82 → 0.72. Both are reported; the official IMD key stays primary. |
| External validation | **Done.** 29 post-2023 events, up from 14. Hybrid POD 7/21 with a CI; alert-burden proxy added. |
| L2 (confidence weights) | Not needed for Window A: every in-window label is `high` confidence. It applies once Window C training uses 2024–25 events. |
| L3 (masking) | Tested in the experiment as `v2_masked`. Effect is small (+0.01 PR-AUC on scoring, none on training). It's kept as a reported variant, not the default. |
| L8 (rainfall-rule tuning) | **Done, not adopted.** `src/tier_tuning.py` searched 32 station-local rules on validation district-day CSI. The best candidate (64.5 mm, fresh rain ≥ 10 mm in 6 h, no susceptibility) scored 0.069 against the default's 0.052, but its CI is [0.025, 0.124] on only 15 validation event-days, and test was unchanged. Adoption rule: the lower CI bound must beat the default, so the IMD default stays. The rule is now a parameter (`rain_rule` in `warning_thresholds.json`, used offline and by the backend), so it can be re-tuned once more labelled months exist. |
| Finding from L8 | On validation, the **rainfall layer** produces 121 ALERT district-days (4 hits). On test, the **ML layer** produces 50 (9 hits). Gauge-level rules can't cut this without losing POD. The structural fix is L5: a district-day model that pools stations and rain sources before deciding. |
| L5 + L7 (district-day model, CWC + USDMA hydromet + ERA5) | **Done, not adopted** (`src/district_day.py`, rule fixed in advance). Every district gets a prediction every day, so coverage is complete. Ranking is real: test ROC-AUC 0.782, PR-AUC 0.24 (base rate 0.068). But there are only 18 training and 15 validation positive district-days, so the CSI-optimal threshold (0.9744) is far too strict: test CSI 0.115 vs hybrid 0.169, external POD 1/29 vs hybrid 7/21. Alert burden falls sharply (25 vs 329 ALERT district-days in monsoon 2024), but by barely alerting. |
| What would move the metrics now | **More labelled positives, not more models.** Every remaining lever is limited by about 50 IMD district-days. Options: (a) retrain on Window C (2023-06 → 2025-12) once a complete 2024–25 event list exists, e.g. from USDMA's daily SEOC reports via RTI; (b) positive-unlabelled learning that treats the 2024–25 documented events as positives and unreported days as unlabelled; (c) use the district-day probability as a **ranking** ("top-3 districts today") rather than a yes/no alert, since ranking is where it is strong. |

Full numbers: `results/label_impact.md` (generated by `scripts/label_impact_report.py`).

---

## 1. Sources on disk (`data/external/labels/`)

| Source | File(s) | Period | Granularity | Role |
|---|---|---|---|---|
| IMD flood inventory (existing) | `data/processed/cleaned/flood_inventory_cleaned.parquet` | 1970 – 2023-08-26 | district, start/end date | **Training labels (v1)** |
| SANDRP compilations | `sandrp/uttarakhand_cloudbursts_2022.html`, `…_2023.html` | May – Oct 2022, 2023 | "DD Month; District: description" (71 + 74 dated entries) | Audit of v1 + Sep–Oct 2023 gap |
| SANDRP event post | `sandrp/pauri_flashflood_2025-08.html` | 6 Aug 2025 | district, block, hour | Validation |
| Sphere India situation reports | `sitreps/*.pdf` (9 files; 4 relevant) | 2023, Jul–Aug 2024, Aug–Sep 2025 | district lists, sometimes the exact place and time | Validation |
| EM-DAT | `emdat/emdat_india_2023_2025.xlsx` → `emdat_uttarakhand_events.csv` | 2023 – 2025 | district only for 2 events | Validation |
| EM-DAT context | `emdat_uttarakhand_context.csv` | multi-week state-wide periods | state | Marks uncertain negatives (never used as positives) |
| Curated news list (existing) | `curated_dataset/flood_inventory/supplement_2024_2025.csv` | 2024 – 2025 | district, place, source URL | Validation |
| CSE Climate India 2024 | `reports/cse_climate_india_2024.pdf` | Jan – Sep 2024 | state; a few stations | Cross-check only |

Not used:
- `sitrep2_india_floods_2024-07-18.pdf`: no Uttarakhand content.
- `situation_report_country_as_on_09-10.pdf`: broken text layer, state-level only.
- `sandrp/prints/`: printouts that are image-only or truncated; the HTML copies replace them.

## 2. Unified schema (one row = one district-day event)

| Column | Notes |
|---|---|
| `event_id` | `<SRC>-<date>-<district code>`, e.g. `SANDRP-2023-07-06-PITH` |
| `date` | event day in IST. For an event "on the night of X/Y", use X if it started before midnight. |
| `district` | one of the 13 canonical names (§3) |
| `place` | village, block or stream as reported |
| `type` | `cloudburst` · `flash_flood` · `debris_flow` · `riverine_flood` · `urban_flood` · `landslide_rain` |
| `hour_local` | optional; when the report gives a time (e.g. Dharali 13:45, Thalisain 07:30–10:30) |
| `deaths`, `missing` | optional; used to grade severity |
| `severity` | `high` (≥ 1 death or ≥ 5 houses lost) · `moderate` · `low` (damage to crops or roads only) |
| `date_confidence` | `high`: exact date and district from a primary report<br>`medium`: date range ≤ 4 days, or an "affected districts" list on a known day<br>`low`: implied or derived |
| `sources` | `;`-separated list of source tags |
| `source_count` | number of independent sources that agree (after de-duplication) |
| `source_ref` | URL, file name or EM-DAT DisNo. |

## 3. Normalisation rules

- **Districts:** map spelling variants to the 13 canonical names:
  - Rudra Prayag → Rudraprayag;
  - Udam Singh Nagar / US Nagar → Udham Singh Nagar;
  - Pauri → Pauri Garhwal;
  - Tehri → Tehri Garhwal;
  - Uttar Kashi → Uttarkashi;
  - Pithoragrah → Pithoragarh.
- **Places to district:** use a small lookup table for places reported without a district, e.g. Joshimath, Tharali and Dewal → Chamoli; Kapkot → Bageshwar; Dharchula → Pithoragarh; Ghansali → Tehri Garhwal; Kedarnath and Ukhimath → Rudraprayag; Raipur, Sahastradhara and Maldevta → Dehradun.
  - Any place we can't map goes to `unresolved.csv` for manual review and is never dropped silently.
- **Exclusions:** these are logged to `excluded.csv` with a reason, not deleted:
  - lightning only;
  - avalanche;
  - snow and hail;
  - drought or heat;
  - **forecast warnings** (IMD/NDMA red alerts);
  - state-only rows;
  - events outside Uttarakhand.
- **Date ranges:** a range of ≤ 4 days becomes one row per day with `medium` confidence. A longer range goes to the context file only.

## 4. Build steps (`scripts/build_labels.py`)

1. **Parse each source into the schema**, one function per source so it can be tested:
   - **SANDRP HTML:** use the regex `^(\d{1,2})\s+(Month);?\s*(District)\s*[:,]`. The year comes from the page. Entries that mention two districts produce two rows.
   - **Sphere situation reports (PDF):**
     - the explicit incidents (place + date) are hand-checked rows kept in `sitreps_manual.csv`, about 15 rows, with page references;
     - an "affected districts" list on a dated report becomes `medium` rows, but only if the report names a triggering date.
   - **EM-DAT:** reuse `emdat_uttarakhand_events.csv` from `scripts/parse_emdat.py`.
   - **Curated list:** load as is. Upgrade SUP-2024-02 (Tehri) to `high`, since Sphere SitRep-1 (5 Aug 2024) pins the date to the night of 31 Jul.
2. **De-duplicate:** the same district within ±1 day is one event. Keep the highest confidence and the earliest specific date, union the sources, and set `source_count`.
3. **Write outputs:**
   - `labels_2022_2025.csv` (positives);
   - `labels_context.csv` (uncertain-negative windows);
   - `excluded.csv` and `unresolved.csv`;
   - `labels_summary.json` (counts by year, district, source and confidence).

## 5. Label audit: IMD v1 vs SANDRP, 2022 – Aug 2023

On the overlap period, at district-day level with ±1 day tolerance, compute:

- **agreement**: IMD days also found in SANDRP;
- **SANDRP-only days**: events IMD missed, i.e. likely false negatives in our training labels;
- **IMD-only days**: often riverine or plains floods, which SANDRP (focused on cloudbursts) does not track;
- a per-district table, to show whether the missing events cluster in particular hill districts.

Output: `results/labels/label_audit.json` and `label_audit.csv`, plus a short section in the Metrics page's validation card.

**Decision gate:** if SANDRP-only events are ≥ 25 % of the IMD count, build **label v2** (IMD ∪ SANDRP, `high`/`medium` only, ±1 day merge) and run it as a *separate experiment*:

- same splits;
- same leave-one-event-out CV;
- same verification suite.

Adopt v2 only if:

- event-CV PR-AUC and CSI improve beyond the bootstrap confidence interval of v1; **and**
- the base rate stays plausible (we expect it to rise; the warning thresholds are re-derived from the new base rate).

## 6. How each period is used

| Period | Labels | Used for | Why |
|---|---|---|---|
| 2022-02 → 2023-08-25 | IMD (v1), or v2 if the gate passes | train / validation / test | complete daily coverage by a single official source |
| 2023-08-26 → 2025-12 | `labels_2022_2025.csv` | **external validation only** | coverage is skewed toward newsworthy events, so a day with no report can't be counted as a day with no flood |
| EM-DAT context windows | none | excluded from scoring | state-wide wet periods with unknown districts |

External validation metrics, computed on the replay with the deployed hybrid tiers:

- **event-level POD**: share of events with ≥ ALERT in the district on day 0 or day −1. Broken down by confidence, type and severity, with a bootstrap CI.
- **warning-time distribution**: the time of the first ≥ ALERT relative to the event hour, where an hour is known.
- **alert burden as a false-alarm proxy**: ALERT+ district-days per monsoon season, and the share of them within ±2 days of a documented event. A true FAR can't be computed because the event list is incomplete.

## 7. Code, tests and UI changes

- `scripts/build_labels.py` (new); `src/label_audit.py` (new).
- `src/external_validation.py`: read `labels_2022_2025.csv` instead of the 14-row supplement; report by confidence and severity; add the alert-burden metric.
- `tests/test_labels.py`:
  - canonical districts only;
  - dates within 2022 – 2025;
  - no duplicate district-days;
  - every row has a `source_ref`;
  - the SANDRP parser finds at least 60 entries on each page.
- `scripts/run_all.py`: add a `labels` stage before `external`.
- `scripts/audit_pipeline.py`: check that the label files exist and are newer than their sources.
- Frontend:
  - **Metrics page:** the External validation card shows N events by source and confidence, POD with a CI, and alert burden.
  - New **"Label audit"** panel: IMD vs SANDRP agreement, with the gaps by district.
  - **Events page:** events are colour-coded by confidence, with a link to the source.
- Docs: a `PRESENTATION_CONTENT.md` section on labels (sources, rules, audit result, honest limits).

## 8. Order of work and checks

| # | Step | Done when |
|---|---|---|
| 0 | L0 alias fix → re-run the full chain → `results/label_impact.md` comparing v0 and L0 | Rudraprayag, USN and Pauri get positives; test added; chain green |
| 1 | Parsers + `sitreps_manual.csv` | each source parses; `unresolved.csv` is reviewed and empty or justified |
| 2 | Merge + de-duplicate → `labels_2022_2025.csv` | `tests/test_labels.py` passes; summary counts look right |
| 3 | IMD vs SANDRP audit | `label_audit.json` written; decision gate evaluated and recorded |
| 4 | External validation on the full list | POD with CI by confidence and severity; alert burden per season |
| 5 | (only if the gate passes) label v2 experiment | v1 vs v2 table under identical CV and verification |
| 6 | UI + docs + `run_all` / audit hooks | full chain green: notebooks, tests, audit with 0 failures |

## 9. Risks and limits (to state openly)

- **Reporting bias:** news-based and SANDRP lists over-represent populated, accessible valleys and fatal events, so POD on them is optimistic for small remote events.
- **Date ambiguity:** night-time cloudbursts get reported on the following day. The ±1 day tolerance and the day-0/day-−1 scoring window absorb this, and it is the reason the rule exists.
- **SANDRP is an NGO compilation** of media and official reports. It is used as corroboration and audit; it does not replace IMD as the training source unless the decision gate passes.
- **Gauge coverage:** some districts have no reporting CWC station on some event days. Those events are reported as "no station data", not as misses.
