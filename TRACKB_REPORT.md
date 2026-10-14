# PRAHAR Space mode: Mapping Flood Damage from Space
*Multimodal AI Hackathon 2026, Track B. Team PRAHAR (VIT). Educational prototype.*

## 1. What the system does
**Input:** an area (W, S, E, N) and a flood date and time.

**Output:** three answers for rescue teams, plus a one-page situation report generated from the maps:
1. **Where did the flood hit?** A flood map from Sentinel-1 radar, before vs after the event, on the same orbit track.
2. **What was damaged?** Pre-event OpenStreetMap buildings, roads and bridges that lie on flooded pixels.
3. **Who is cut off?** Settlements that lose their road connection to the nearest hospital or town (or, if none is mapped, the edge of the area), from a road-network graph with flooded segments and bridges removed.

Run end to end from raw data for any area and date:
```bash
python -m src.space.run    --name <event> --bbox W,S,E,N --date "YYYY-MM-DD HH:MM"   # UTC
python -m src.space.report --name <event>   # writes results/space/<event>/sitrep.md + sitrep.html
```
Outputs go to `results/space/<event>/`: `flood_class.tif`, `flood_class_rule.tif`, `*_hit.geojson`, `cutoff.json`, `summary.json` and `map.png`.

## 2. Inputs: only those Track B allows
| Input | Source (keyless) | Use |
|---|---|---|
| Sentinel-1 (VV, VH) | Microsoft Planetary Computer `sentinel-1-rtc` STAC | before and after pairs from the **same relative orbit**, plus a second pre-event image for the AI |
| Sentinel-2 L2A | Element 84 Earth Search STAC | when the sky is clear (monsoon scenes were > 55 % cloud at Dharali, so not used there) |
| Copernicus DEM GLO-30 | AWS Open Data `copernicus-dem-30m` | radar layover/shadow geometry, DEM input to the AI |
| OpenStreetMap **before the event** | ohsome API, `elementsFullHistory/geometry`, keeping versions valid at the snapshot date | buildings, roads, bridges, places, hospitals, waterways, water areas |
| Kuro Siwo GRD | Hugging Face `orion-ai-lab/Kuro-Siwo-Webdataset` | training and testing the segmentation model |

Copernicus EMS / UNOSAT maps and post-event OSM are **not** used as inputs. The anonymous ohsome `/elements/geometry` endpoint is blocked, so the full-history endpoint is filtered to the snapshot date. This returns the same features.

## 3. Method
**3.1 Rule baseline: the UN-SPIDER Recommended Practice (UNOOSA).**
- VH in dB, 50 m circular smoothing.
- Difference = after / before, flooded where the difference is > 1.25.
- Permanent water masked; pixels with ≤ 8 connected neighbours removed.

Two documented adaptations, plus one corridor rule:
1. **Mountains.** The practice's slope > 5 % mask removed **99.6 %** of the Dharali valley (263.6 of 264.6 km²). We replaced it with the standard SAR geometry masks:
   - layover where terrain facing the radar is steeper than the local incidence angle;
   - shadow where terrain facing away is steeper than 90° minus the incidence angle;
   - incidence from Sentinel-1 IW's 29.1°–46.0° range across the swath; computed per orbit from GLO-30.

   Only 1.1 km² is then hidden from both orbits.
2. **Permanent water** comes from pre-event OSM water areas, because JRC Global Surface Water is not an allowed input.
3. **Corridor.** Detections are kept only within **200 m of a pre-event mapped river or stream**. This is the Uttarakhand High Court's (2013) river no-construction corridor. Without it, a 12-day monsoon pair flags whole wet hillsides.

**3.2 AI component: flood segmentation (primary detector).**
- **Model:** U-Net with a ResNet-34 encoder, 7 input channels: post-event VV and VH, pre-event 1 VV and VH, pre-event 2 VV and VH (all in dB), and the DEM minus its chip mean. 3 output classes: no water, permanent water, flood.
- **Training:** Kuro Siwo GRD, official train split, streamed from Hugging Face. Loss = cross-entropy + Dice. AdamW, mixed precision, Colab T4. Two time-boxed runs:
  1. 750 steps on 2 shards;
  2. continued for **1,606 more steps** with a stronger flood class weight (3.0), cosine learning rate, and the 3 shards the first run never saw.
- **Decision threshold:** the flood-probability cut-off (**0.80**) was chosen to maximise F1 on the **validation** split (unseen events). The test split was used once, afterwards.
- **Export:** ONNX, run on CPU by `src/space/ai.py`, which applies the same threshold.

**3.3 Damage and cut-off** (`src/space/impact.py`):
- An object counts as **hit** if any flooded pixel touches it (direct overlay, no scoring).
- The road graph is built from pre-event OSM lines, weighted by length. Hit roads and bridges are removed. Dijkstra shortest paths to the destinations; settlement status is *cut off*, *longer route*, *connected*, or *not connected even before the flood*.

## 4. Results
**4.1 AI model on unseen Kuro Siwo test events** (official test split, never seen in training or threshold selection; 3,000 chips):

| Flood class | Run 1 (750 steps, arg-max) | Run 2, arg-max | **Run 2, tuned threshold 0.80** |
|---|---|---|---|
| Precision | 0.566 | 0.592 | **0.739** |
| Recall | 0.168 | 0.892 | **0.823** |
| F1 | 0.259 | 0.712 | **0.779** |
| IoU | 0.149 | 0.553 | **0.638** |

**Any water** (permanent + flood, threshold 0.925): precision 0.861, recall 0.720, **F1 0.784**, IoU 0.645.

Reading: run 1 was badly under-trained, finding only 17 % of flooded pixels. More training on unseen shards lifted recall to 89 %. The validation-chosen threshold then traded a little recall for much higher precision. Now about 3 in 4 pixels called flooded are flooded, and about 4 in 5 flooded pixels are found.

**4.2 Unseen Himalayan scene: Dharali, Uttarkashi (5 Aug 2025, 08:15 UTC).**

AOI 78.70–78.90 E, 30.98–31.10 N (265 km²). Radar pairs:
- track 129 ascending: 24 Jul → **5 Aug 12:48 UTC**, about 4.5 h after the flood;
- track 63 descending: 1 Aug → 7 Aug.

| | **AI floodwater** (run 2, threshold 0.80) | Possible debris (rule radar change, low confidence) |
|---|---|---|
| Area inside the 200 m corridor | **0.74 km²** | 4.77 km² |
| Buildings on it (of 502 pre-event OSM) | **0** | 47 |
| Road segments (of 112) | **0** | 23 |
| Bridges (of 16) | **0** | 1 |
| Settlements cut off (of 14 mapped places) | **0** | 6: Bagori, Bhaironghati, Dhakroliya, Halunga, **Harsil**, Lanka |

**Why the AI map is nearly empty at Dharali:** the disaster was a **debris flow** of mud and boulders that buried the village, not standing floodwater. The U-Net is trained on Kuro Siwo *floodwater* labels, so it correctly does not call rough debris "water".
- The under-trained run-1 model had flagged 9 buildings there. Those were most likely false positives; run 2's much higher precision on unseen events supports that.
- Damage from debris is therefore reported from a separate, clearly labelled low-confidence layer: the rule-based radar change, after/before < 1/1.25 within the corridor.
- That layer's cut-off result (Harsil and five other settlements) is consistent with reports that the road at Harsil was washed out, but the layer itself has not been validated.

Figure: `results/space/dharali/map.png`. The dashboard's "Space mode" page shows both layers interactively.

**4.3 Case study, Trishuli (Aug 2026) vs EMSR927: not completed.** The pipeline runs on any area (the ohsome snapshot is clamped to 27 Jul 2026, as the brief instructs), but the comparison against EMSR927 was not finished before the deadline. We report this rather than show unverified numbers.

## 5. Limitations (what the system cannot do)
- **Revisit.** Sentinel-1 passes every 6–12 days. The map shows what the satellite saw on that pass, not the peak of the flood, and it **cannot warn** of a sudden glacier collapse or cloudburst.
- **Steep terrain.** Radar layover and shadow hide parts of narrow gorges. Only local (active) layover/shadow is modelled; shadow cast by distant ridges is not.
- **Monsoon change.** Between two passes 12 days apart, wet slopes and vegetation change the backscatter. The rule baseline over-detects; the 200 m corridor limits but does not remove this.
- **AI model.** F1 0.78 on Kuro Siwo's unseen test events, which are mostly lowland and river floods. Himalayan gorges differ, and there are no labelled Himalayan scenes to measure on. It was trained on GRD σ⁰ but run on RTC γ⁰, which shifts the input distribution. Debris deposits are not a separate class, and training was time-boxed (about 2,350 steps in total).
- **OSM.** Buildings and roads that aren't mapped can't be counted. "Hit" means the object lies on a flooded pixel, not that it is structurally damaged. Settlement-to-road snapping can misplace hamlets.
- Sentinel-2 is unusable under monsoon cloud.
- Results are estimates for an educational prototype. Verify on the ground before any operational use.

## 6. Attribution and citations
- Contains modified Copernicus Sentinel data 2025–2026.
- Produced using Copernicus WorldDEM-30 © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018 provided under COPERNICUS by the European Union and ESA; all rights reserved.
- © OpenStreetMap contributors.
- Bountos, N.I. et al. (2024). *Kuro Siwo: 33 billion m² under the water. A global multi-temporal satellite dataset for rapid flood mapping.* NeurIPS Datasets & Benchmarks. CC BY 4.0.
- UN-SPIDER (UNOOSA). *Recommended Practice: Flood Mapping and Damage Assessment using Sentinel-1 SAR Data in Google Earth Engine.*
- Copernicus Global Flood Monitoring, Product User Manual v4.0 (2025): exclusion-mask concepts (radar shadow, topography).
- Uttarakhand High Court (Aug 2013), 200 m river corridor; NGT (2017) river setbacks.
