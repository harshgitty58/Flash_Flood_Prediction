# PRAHAR presentation cheat-sheet (21 Oct 2026)

Every number below is what the app shows. Each one is read from `web/public/data/*.json`, which the pipeline exports.

## 1. Thirty-second pitch
> Uttarakhand loses lives every monsoon to flash floods that arrive in hours. PRAHAR fuses CWC rain and river gauges, flood and landslide history and district indices into a calibrated flood probability for the next 24 hours. It combines that with IMD rainfall rules into five warning tiers, says how sure it is, explains why, and shows which buildings, roads and bridges sit inside official river-setback zones. We evaluated it honestly: on held-out months, on held-out events, and on 29 floods that happened after training ended.

## 2. Numbers to say

| Say | What it means | Where on screen |
|---|---|---|
| **518,304 station-hours** · 44 rain gauges + 7 river gauges · 13 districts · 2022 → Sep 2026 | the hourly multi-source table | Landing → numbers band |
| **126,904 labelled hours**; labels end 26 Aug 2023 | after that, "no report" ≠ "no flood", so later hours are replay | Data & Model |
| **5 silent data bugs fixed** (47 % of rain rows lost to timestamps; 58 % fake dry hours; label off by a day; a 272 mm/h faulty gauge; 13 of 29 flood days dropped by district spellings) | why the numbers are trustworthy now | Metrics → Ground truth |
| Test month (Aug 2023), XGBoost: **ROC-AUC 0.71, PR-AUC 0.15** (base rate 0.058, so **2.6× better than chance**), F1 0.32, MCC 0.30 | ranking quality on an unseen month | Metrics → hour-level table |
| Leave-one-event-out: **ROC-AUC 0.70**, PR-AUC 0.19 (base 0.081) | holds up across individual flood episodes | Data & Model → event CV |
| Hybrid tiers ≥ ALERT: **precision 0.23, recall 0.65** (station-hour, test) | 2 of 3 flood hours flagged | Metrics → layer contribution |
| District-day CSI (strict WMO): **0.095** vs district prior **0.036** and persistence **0.053** (POD 0.70, FAR 0.90) | 2–3× the baselines, modest in absolute terms | Metrics → verification panel |
| External validation: **7 of 21** documented floods after training caught (POD 0.33, 95 % CI 0.14–0.52), e.g. the Kedarnath trek route (31 Jul 2024), Dharali (5 Aug 2025) | independent events, never used in training | Metrics → external validation |
| **BSS 0.073** vs climatology · **ECE 0.012** | probabilities are calibrated and beat climatology | Metrics → probabilistic skill |
| Conformal 90 % sets: **100 % of floods covered**; 85 % of hours "uncertain" | it says "can't tell" when the data can't tell | Uncertainty |
| Fusion ablation (event-CV ROC): rain only **0.50** → + discharge 0.55 → + flood history **0.77**; deployed (static history) 0.70 | what each source adds; rain at the gauge alone can't see cloudbursts | Uncertainty → what each source adds |
| Robustness: 20 % rain noise → ROC −0.004; 25 % of inputs dropped → −0.07; flood history removed → 0.50 | which failures matter | Uncertainty → what if a source fails |
| Lead time: **6 of 18** floods warned before the event day, median **3.5 h**; 7 already on as a baseline, 5 missed | honest switch-on lead | Forecast (stat card) · Metrics → honest lead time |
| Impact: **261,030 buildings** within 5 km of the 27 reporting gauges; **10,297** at MODERATE or above; 228 bridges; zones 50 / 100 / 200 m (NGT 2017, Jal Shakti 2025, Uttarakhand HC 2013) | an exposure proxy in official setback zones, not inundation | Impact |
| Latency: `/predict` **17 ms p95**; buildings per view **66 MB → 0.74 MB**; calibration **4.3 → 0.006 ms** | engineered for live use | System |
| **47 tests** (data, labels, terrain, API and security), pipeline audit **0 fail / 0 warn**, 28-stage `run_all.py`, CI on GitHub | reproducible | (terminal) / GitHub Actions |

## 3. Demo click path (about 3 minutes)
1. **Landing.** Hero, then scroll to **"Verified results"** (four numbers with CIs). Open the console.
2. **Overview.** The replay is 12 Sep 2024 19:00.
   - **EXTREME at Haldwani**: the screen shows **141 mm** in 24 h (140.5), set by the rainfall rule; the ML tier says NORMAL ("ML 2 %").
   - 5 stations ≥ SEVERE; 27 of 44 gauges reporting.
   - "Districts to watch" ranking.
3. **Risk Map.** Satellite → click **Pithoragarh**. The drawer shows SEVERE by rainfall (90.5 mm) while ML says NORMAL, with an UNCERTAIN 90 % set and SHAP drivers. *"The two layers disagree, and we show both."*
4. **Impact.** Search "Haldwani" → building outlines by class → click a building (zone, distance to river, tier).
5. **Uncertainty.** The fusion ablation bar chart plus the sensor-failure table.
6. **Metrics.** The verification panel (CSI vs baselines), then the external-validation table with source links.
7. **Close:** the data story and the limits.

## 4. Likely questions and short answers
- **"Why is CSI so low?"**
  - Flash floods are rare and very local.
  - Half the documented floods had less than 50 mm in 24 h at the district's wettest gauge, so the gauges never saw the cloudburst.
  - It's still 2–3× the baselines. We report the honest number, not a flattering one.
- **"Why PR-AUC and not accuracy?"** Floods are 4–8 % of hours, so "never flood" scores 94 % accuracy. PR-AUC is judged against the base rate.
- **"Any leakage?"**
  - Chronological splits.
  - Past-only features, with a truncation test.
  - Labels never feed features.
  - Leave-one-event-out with a ±7-day buffer.
  - We removed latitude and longitude when we found they carried 38 % of the importance: the model was memorising *where*.
- **"Why not deep learning?"** About 50 flood district-days in training. A deep net would memorise them. The brief's ladder (LR → RF → XGBoost + conformal + SHAP) fits tabular, small-label data.
- **"Probability 1.8 % but EXTREME?"** The tier is the higher of two layers. Here the IMD rainfall rule fired (141 mm/24 h ≥ 115.6 mm "very heavy", raised one level for a landslide-prone, flood-prone district); the ML layer said NORMAL. The trigger is shown on every station.
- **"What does conformal give you?"** A coverage guarantee. At 90 % it covered every flood hour. It answers "uncertain" most of the time, which is the honest answer with gauge-only inputs. Known limit: the 80 % and 90 % sets coincide (coarse calibrated probabilities), and the fix is in the plan.
- **"Soil moisture, terrain?"** Built (ERA5-Land soil moisture, DEM terrain at each gauge; experiment H, ROC 0.703) but not adopted. It didn't beat the deployed model on held-out events. The next data step is satellite rain (GPM IMERG), which can see between the gauges.
- **"Lead time?"** 6 of 18 warned before the event day, median 3.5 h. It's a nowcast with no weather-forecast input. Longer lead needs IMERG and forecast fields.
- **"Is the impact map an inundation map?"** No. It's exposure in official river-setback zones, crossed with the hazard tier, and it says so on screen.
- **"How good are the labels?"** We audited IMD against SANDRP: SANDRP documents 40 events IMD misses. We tested a merged label set (v2) under a rule fixed in advance, and didn't adopt it.
- **"Himachal and Sikkim?"** The brief makes v1 Uttarakhand-only. The pipeline is state-agnostic, and expansion is planned (`PRAHAR_MASTER_PLAN.md`, WS-23).
- **"What about the satellite / Track B work?"** That was a separate hackathon entry, archived in `../hackathon track-b/`. This project is the early-warning system.
- **"What's next?"** `PRAHAR_MASTER_PLAN.md`:
  - 2001–2025 labels and a district-day model trained on 25 monsoons of gridded data;
  - IMERG rain;
  - fixed calibration;
  - a database, alerts and a sitrep PDF.

## 5. Avoid saying
- "Predicts floods with X % accuracy". Use PR-AUC, CSI and POD with the base rates instead.
- "Inundation depth" or "damage estimate". It's an exposure proxy.
- "36 h lead time". That was an older event-CV definition; the honest number is 3.5 h median.
- "District-day CSI 0.17" without its definition. 0.17 counts "flood today **or tomorrow**"; the strict figure on screen is 0.095.

## 6. If something breaks
- **Static mode needs no API:** `cd web && npm run dev` → http://localhost:5173. Every page reads `web/public/data`.
- **With the API:** `python -m uvicorn backend.app:app --port 8000`, then `cd web && npm run dev:api`.
- **Use the right Python:** `C:\Users\HP\anaconda3\python.exe`, which has every dependency. The default `python` (3.13) lacks pandas.
- The deployed API on Render's free tier sleeps when idle. Open it about 1 minute before presenting, or demo locally.
