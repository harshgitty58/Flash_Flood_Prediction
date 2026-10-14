# Situation report — Dharali (event 2025-08-05 08:15 UTC)

*Generated automatically by PRAHAR Space mode from Sentinel-1 radar, Copernicus DEM and pre-event OpenStreetMap (2025-08-04). Every number below comes from the system's maps.*

## Where did the flood hit?
- Detector: **AI U-Net (Kuro Siwo) within the 200 m river corridor**.
- Flooded area inside the 200 m river corridor: **4.656 km²** (whole area: 10.474 km²).
- Radar pairs used (same orbit): track 129 ascending 2025-07-24 → 2025-08-05 12:48; track 63 descending 2025-08-01 → 2025-08-07 00:42.
- Not analysable: radar layover/shadow on 1.087 km²; permanent water 1.152 km².

## What was damaged? (pre-event OSM objects on flooded pixels)
- Buildings: **9 of 502**
- Road segments: **14 of 112** · Bridges: **1 of 16**

## Who is cut off? (road connection to nearest AOI exit)
- **6 settlements cut off**: Bagori, Bhaironghati, Dhakroliya, Halunga, Harsil, Lanka.
- 0 reachable only by a longer route; 4 still connected; 4 had no mapped road link even before the flood.

## Model reliability
- U-Net trained on Kuro Siwo; on unseen test events: flood precision 0.5655, recall 0.1676, F1 0.2586, IoU 0.1485.
- Read as: when it says 'flooded' it is right about half the time; it misses many flooded pixels.

## Limitations (read before acting)
- Sentinel-1 revisits every 6–12 days: this maps what the satellite saw, not the moment of the flood, and cannot warn in advance.
- Steep Himalayan slopes cause radar layover/shadow; narrow gorges and debris under forest can be missed.
- OSM completeness varies; unmapped buildings and roads cannot be counted. Damage = 'on a flooded pixel', not structural damage.
- Educational prototype — verify on the ground before operational use.

*Contains modified Copernicus Sentinel data 2025–2026. Produced using Copernicus WorldDEM-30 © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018 provided under COPERNICUS by the European Union and ESA; all rights reserved. © OpenStreetMap contributors (pre-event snapshot via the ohsome API). Training data: Kuro Siwo (Bountos et al., NeurIPS 2024, CC BY 4.0).*