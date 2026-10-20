# Terrain at gauges: Copernicus GLO-30 (30 m)

51 of 51 gauges processed with `src/terrain.py` (0.2° window each; channels = upstream area ≥ 1 km²). Attribution: Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018, provided under COPERNICUS by the EU and ESA.

|                    |    mean |    min |    50% |     max |
|:-------------------|--------:|-------:|-------:|--------:|
| elev_m             | 1048.19 | 211.6  | 867.6  | 3128.7  |
| slope_deg          |   14.01 |   0.22 |  12.66 |   46.5  |
| tri_m              |   21.48 |   1.63 |  18.33 |   78.05 |
| twi                |    6.48 |   4.26 |   5.87 |   15.22 |
| spi                |    2.83 |  -1.22 |   2.57 |   13.21 |
| hand_m             |   78.06 |   0    |  16.69 |  551.46 |
| dist_channel_m     |  338.47 |   0    | 243.2  | 1066.2  |
| relief_1km_m       |  386.06 |  13.4  | 437.3  | 1057.6  |
| slope_mean_1km_deg |   17.63 |   0.91 |  19.25 |   38.1  |

Check against the Terrarium DEM used until now (44 gauges): elevation r = 1.000, median |difference| = 4.0 m; slope r = 0.842 (slope differs more because GLO-30 is 30 m against ~38 m and is computed with the Horn method here).

`upstream_truncated` = True for 0 gauges (their river drains in from outside the window; basin area comes with HydroSHEDS).
