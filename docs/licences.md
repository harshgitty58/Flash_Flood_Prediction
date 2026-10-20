# Data licences and attribution

What PRAHAR uses, under which terms, and what that obliges us to do. This is task WS-22.1 of `PRAHAR_MASTER_PLAN.md`.

The rule for redistribution: **derived data goes in the repository; raw third-party archives do not.** That is why `data/external/` is git-ignored except for the derived label CSVs.

| Data | Used for | Licence / terms | Obligation | In git? |
|---|---|---|---|---|
| CWC telemetry rainfall and river discharge (India-WRIS) | gauge observations | Government of India open data (NDSAP) | attribute CWC / India-WRIS | yes (`curated_dataset/`, pinned by `MANIFEST.sha256`) |
| USDMA hydromet station reports | district-day rain | public portal (sfo.usdma.in) | attribute USDMA | no (`data/external/hydromet/`) |
| IMD flood event inventory, DFSI, district indices | labels v1, history features | IMD / curated public sources | attribute IMD | yes (`curated_dataset/flood_inventory/`) |
| GSI landslide inventory (Bhukosh) | landslide features | GSI terms | attribute GSI / Bhukosh | yes (`curated_dataset/landslide/`) |
| ERA5 / ERA5-Land via Open-Meteo | reanalysis rain, soil moisture | Copernicus licence (free, attribution); Open-Meteo CC BY 4.0 | "Contains modified Copernicus Climate Change Service information"; credit Open-Meteo | no |
| Copernicus DEM GLO-30 (AWS open data) | terrain at gauges (`scripts/terrain_at_gauges.py`) | Copernicus DEM licence | "Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the EU and ESA; all rights reserved" | no (window cache in `data/external/glo30/`); derived values yes (`results/v3/terrain_at_gauges.csv`) |
| AWS Terrain Tiles (Terrarium) | impact-layer height above river; earlier gauge terrain | open (Mapzen / AWS; SRTM, GMTED and others) | attribute "AWS Terrain Tiles" and the underlying sources | no |
| Microsoft Global ML Building Footprints | buildings in the impact layer | ODbL | attribute; share-alike on the derived building database (`web/public/data/bld/`) | derived tiles yes (ODbL applies) |
| OpenStreetMap (Overpass) | rivers, roads, bridges, POIs, place names | ODbL | "© OpenStreetMap contributors"; share-alike on derived databases | derived yes (ODbL applies) |
| GeoNames | place names | CC BY 4.0 | attribute GeoNames | no |
| SANDRP cloudburst compilations | label audit, labels v2 | publisher copyright | store facts (date, district, place) and the URL only; no article text | facts yes (`data/external/labels/*.csv`); HTML no |
| Sphere India / MHA NDMI situation reports | labels | public government and NGO reports | cite the report; facts and URL only | facts yes; PDFs no |
| EM-DAT (CRED) | labels | registration; non-commercial; no redistribution of raw rows | cite EM-DAT; ship derived district-days only | no (`emdat_*` excluded) |
| Sentinel-2 L2A (Earth Search, AWS) | landing-page landscape images | Copernicus Sentinel data licence | "Contains modified Copernicus Sentinel data 2024-2025" | yes (`web/public/img/home/`) |
| Wikimedia Commons photos (Mukerjee; sumit; Nitin Maletha) | landing page | CC BY-SA 3.0 / 4.0 | credit the authors; edited images shared under the same licence | yes, credited on the page |
| Basemaps (CARTO, Esri World Imagery, OpenTopoMap) | map backgrounds | provider terms | on-map attribution (present) | no (fetched at run time) |

**Disclaimer**, shown on every page and in every export: *PRAHAR is a decision-support prototype, not an official warning. Follow IMD, USDMA and district administration advisories.*
