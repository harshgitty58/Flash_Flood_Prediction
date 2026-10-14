# Situation report — Dharali (event 2025-08-05 08:15 UTC)

*Generated automatically by PRAHAR Space mode from Sentinel-1 radar, Copernicus DEM and pre-event OpenStreetMap (2025-08-04). Every number below comes from the system's maps.*

## Where did the flood hit?
- Detector: **AI U-Net (Kuro Siwo) within the 200 m river corridor**.
- Flooded area inside the 200 m river corridor: **0.735 km²** (whole area: 2.136 km²).
- Radar pairs used (same orbit): track 129 ascending 2025-07-24 → 2025-08-05 12:48; track 63 descending 2025-08-01 → 2025-08-07 00:42.
- Not analysable: radar layover/shadow on 1.087 km²; permanent water 1.152 km².

## What was damaged? (pre-event OSM objects on flooded pixels)
- Buildings: **0 of 502**
- Road segments: **0 of 112** · Bridges: **0 of 16**

## Who is cut off? (road connection to nearest AOI exit)
- **0 settlements cut off**: none.
- 0 reachable only by a longer route; 10 still connected; 4 had no mapped road link even before the flood.

## Possible debris (low confidence)
- The AI model maps floodwater only. A rule-based radar-change layer marks **4.771 km²** of possible debris / ground change in the corridor (not validated).
- On it: buildings 47 of 502, road segments 23 of 112, bridges 1 of 16; settlements cut off if those roads are blocked: 6.

## Model reliability
- U-Net trained on Kuro Siwo; on unseen test events: flood precision 0.7392, recall 0.823, F1 0.7789, IoU 0.6378 (flood threshold 0.8, chosen on validation).
- Read as: about 74 % of pixels it calls flooded are flooded, and it finds about 82 % of flooded pixels.

## Limitations (read before acting)
- Sentinel-1 revisits every 6–12 days: this maps what the satellite saw, not the moment of the flood, and cannot warn in advance.
- Steep Himalayan slopes cause radar layover/shadow; narrow gorges and debris under forest can be missed.
- OSM completeness varies; unmapped buildings and roads cannot be counted. Damage = 'on a flooded pixel', not structural damage.
- Educational prototype — verify on the ground before operational use.

*Contains modified Copernicus Sentinel data 2025–2026. Produced using Copernicus WorldDEM-30 © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018 provided under COPERNICUS by the European Union and ESA; all rights reserved. © OpenStreetMap contributors (pre-event snapshot via the ohsome API). Training data: Kuro Siwo (Bountos et al., NeurIPS 2024, CC BY 4.0).*