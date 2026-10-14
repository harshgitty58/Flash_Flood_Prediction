# PRAHAR: Map Coverage Plan (places without prediction or building scan)

**Why there are gaps:** a building is scanned and scored only within **5 km of a rain gauge that was reporting at the replay time** (27 of 44 gauges). Without a live gauge there is no hazard input, and colouring buildings "minimal risk" there would be false reassurance.

**Audit (2026-10-13):** of 53 prominent places (GeoNames towns plus pilgrimage and event sites), **12 are covered and 41 are not**.

## 1. Gap list, by what can fix it

### A. A gauge is close, but was offline at the replay time
These are fixable with the gauge's last report, marked as stale.

| Place | Gauge | Distance |
|---|---|---|
| Badrinath | Badrinath_1 | 0.2 km |
| Rudrapur | Rudrapur_2 | 0.7 km |
| Almora | Almora_1 | 0.8 km |
| Birbhaddar | Virbhadra | 0.9 km |
| Rishikesh | Virbhadra | 3.7 km |
| Vikasnagar | Dakpathar | 4.0 km |

### B. No gauge within 5 km
These need a different hazard source.
- **Big towns:** Dehradun 18 km from a gauge, Haridwar 12 km, Roorkee 9 km, Haldwani area towns (Kashipur, Ramnagar, Kichha, Khatima, Jaspur, Bazpur), Pauri, Tehri, Lansdowne, Ranikhet, Bageshwar.
- **High-risk pilgrimage and event sites:** Kedarnath 13 km, Joshimath 22 km, Dharali 8 km, Gangotri, Yamunotri, Tharali, Ukhimath, Munsiyari.

## 2. Plan

| Step | What | Hazard source and label | Effort |
|---|---|---|---|
| **0 (done)** | Hover tooltip at zoom ≥ 11 outside coverage: "Data unavailable", the nearest reporting gauge and its distance, and whether a nearby gauge was offline | none | done |
| 1 | **Stale-gauge coverage (group A).** For each offline gauge, use its last valid replay hour within 7 days. Scan buildings within 5 km. Colour by that hour's tier with a dashed outline and "last report: <time>". Older than 7 days → stays "unavailable". | the deployed hybrid tier at the gauge's last report | ~2 h |
| 2 | **Town coverage from the district outlook (group B).** Scan buildings within 3 km of each listed town and site. Colour by the **district-day outlook** (pooled district model, `src/district_pooled.py`), using a separate muted palette and the label "district estimate, not a gauge reading". | district-day probability (CWC + USDMA hydromet + ERA5); it ranks districts better than history (recall@3 0.34 vs 0.21) but was **not** adopted as an alert, so it is shown as context only | ~½ day |
| 3 | **Real fix (data):** add USDMA state weather stations as live gauges. Their coordinates aren't in the CSV export, so they'd need geocoding from the station address, or a request to USDMA. Longer term, radar or IMERG rain. | gauge-grade hazard | data-dependent |

## 3. Guardrails
- Every building keeps a `source` field (`gauge` / `stale_gauge` / `district_outlook`). The object card states it, and the legend separates the three.
- District-outlook buildings never count towards "exposed buildings" totals or impact KPIs, which stay gauge-based.
- Size: step 2 adds roughly 150–250k buildings (mostly Dehradun, Haridwar and the Haldwani belt). They load as viewport tiles like today, so per-view weight is unchanged.

**Recommendation:** do step 1 now (cheap and honest). Do step 2 only if the demo needs Dehradun, Haridwar and the Char Dham towns lit up, and keep it visibly marked as a district estimate.
