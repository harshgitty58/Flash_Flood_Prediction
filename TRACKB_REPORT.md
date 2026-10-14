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
- **Model:** U-Net with a ResNet-34 encoder (ImageNet initialisation), 7 input channels: post-event VV and VH, pre-event 1 VV and VH, pre-event 2 VV and VH (all in dB), and the DEM minus its chip mean. 3 output classes: no water, permanent water, flood.
- **Training:** Kuro Siwo GRD, official train split, streamed. Loss = cross-entropy (class weights 0.4 / 1 / 2) + Dice. AdamW, mixed precision, Colab T4.
- **Budget:** the deadline allowed **750 steps (1 partial epoch, 2 of 5 shards)**.
- **Export:** ONNX, run on CPU by `src/space/ai.py`, in 224-pixel chips.

**3.3 Damage and cut-off** (`src/space/impact.py`):
- An object counts as **hit** if any flooded pixel touches it (direct overlay, no scoring).
- The road graph is built from pre-event OSM lines, weighted by length. Hit roads and bridges are removed. Dijkstra shortest paths to the destinations; settlement status is *cut off*, *longer route*, *connected*, or *not connected even before the flood*.

## 4. Results
**4.1 AI model on unseen Kuro Siwo test events** (official test split, never seen in training; 3,000 chips):

| Class | IoU | | Flood | Value |
|---|---|---|---|---|
| no water | 0.964 | | precision | **0.566** |
| permanent water | 0.000 | | recall | **0.168** |
| flood | **0.149** | | F1 | **0.259** |

Confusion matrix (pixels; rows = truth, columns = prediction; order no water / permanent / flood):

```
[[141,505,638   17,424   140,505]
 [  1,253,085        0   449,052]
 [  3,810,400        0   767,366]]
```

Reading: when the model says "flood", it is right 57 % of the time, but it finds only 17 % of flooded pixels. It never learned "permanent water"; those pixels go to "flood" or "no water". This is the result of a deadline-limited 750-step run, not a converged model.

**4.2 Unseen Himalayan scene: Dharali, Uttarkashi (5 Aug 2025, 08:15 UTC).**

AOI 78.70–78.90 E, 30.98–31.10 N (265 km²). Radar pairs:
- track 129 ascending: 24 Jul → **5 Aug 12:48 UTC**, about 4.5 h after the flood;
- track 63 descending: 1 Aug → 7 Aug.

| | Rule baseline | **AI model** |
|---|---|---|
| Flooded area inside the 200 m corridor | 13.1 km² | **4.66 km²** |
| Buildings hit (of 502 pre-event OSM) | 69 | **9** |
| Road segments hit (of 112) | 40 | **14** |
| Bridges hit (of 16) | 3 | **1** |
| Settlements cut off (of 14 mapped places) | 8 | **6**: Bagori, Bhaironghati, Dhakroliya, Halunga, **Harsil**, Lanka |

The road from Harsil towards Dharali was reported washed out after the event, so Harsil being cut off matches the reports. The rest of the AI map has not been independently validated: no Copernicus EMS activation was checked for this event in the time available. Figure: `results/space/dharali/map.png`.

**4.3 Case study, Trishuli (Aug 2026) vs EMSR927: not completed.** The pipeline runs on any area (the ohsome snapshot is clamped to 27 Jul 2026, as the brief instructs), but the comparison against EMSR927 was not finished before the deadline. We report this rather than show unverified numbers.

## 5. Limitations (what the system cannot do)
- **Revisit.** Sentinel-1 passes every 6–12 days. The map shows what the satellite saw on that pass, not the peak of the flood, and it **cannot warn** of a sudden glacier collapse or cloudburst.
- **Steep terrain.** Radar layover and shadow hide parts of narrow gorges. Only local (active) layover/shadow is modelled; shadow cast by distant ridges is not.
- **Monsoon change.** Between two passes 12 days apart, wet slopes and vegetation change the backscatter. The rule baseline over-detects; the 200 m corridor limits but does not remove this.
- **AI model.** Low recall (0.17) and no permanent-water skill after only 750 steps. It was trained on GRD σ⁰ but run on RTC γ⁰, which shifts the input distribution. Debris deposits are not a separate class.
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
