# Flood Intelligence Platform — Multimodal & Uncertainty-Aware Flash-Flood Prediction

> **Project concept:** A multimodal, uncertainty-aware flood intelligence platform for hilly regions of India that predicts flash-flood risk, estimates when risk may peak, visualizes where flooding may occur, and translates the forecast into building/infrastructure exposure.

---

## 1. Core Product Vision

The system should not stop at:

> **“Flood probability = 82%.”**

Instead, it should answer the complete chain:

> **Will flooding happen? → When? → Where? → How certain are we? → What could be affected? → How severe could the impact be?**

### Core product loop

```text
PREDICT
   ↓
EXPLAIN
   ↓
LOCATE
   ↓
QUANTIFY IMPACT
   ↓
SHOW UNCERTAINTY
```

The platform combines multiple environmental and geospatial data sources and produces a decision-support view for disaster-management analysts, authorities, researchers, and field users.

---

# 2. Main System Architecture

```text
                         DATA SOURCES
 ┌────────────┬────────────┬────────────┬────────────┬─────────────┐
 │ Satellite  │ Rainfall   │ River      │ Soil       │ DEM/Terrain │
 │ Imagery    │            │ Level      │ Moisture   │             │
 └──────┬─────┴─────┬──────┴──────┬─────┴──────┬─────┴──────┬──────┘
        │            │             │            │             │
        └────────────┴─────────────┴────────────┴─────────────┘
                              ↓
                    DATA INGESTION & QA
                              ↓
                 CLEANING / NORMALIZATION
                              ↓
                MULTIMODAL FEATURE FUSION
                              ↓
                    FLOOD RISK MODEL
                              ↓
          ┌───────────────────┼────────────────────┐
          ↓                   ↓                    ↓
   FLOOD PROBABILITY     UNCERTAINTY         FORECAST WINDOW
          │                   │                    │
          └───────────────────┴────────────────────┘
                              ↓
                 INUNDATION / FLOOD EXTENT
                              ↓
              ┌───────────────┴────────────────┐
              ↓                                ↓
       BUILDING FOOTPRINTS                GIS ASSETS
              ↓                                ↓
       BUILDING EXPOSURE             ROADS / BRIDGES /
              │                       SCHOOLS / HOSPITALS /
              │                       SETTLEMENTS
              └───────────────┬────────────────┘
                              ↓
                      IMPACT ENGINE
                              ↓
                 WEB/PWA + MOBILE INTERFACE
```

---

# 3. Key Output Categories

## 3.1 Flood Probability

A continuous probability score:

```text
0–20%   → Low
20–50%  → Moderate
50–75%  → High
75–100% → Very High
```

Example:

> **Flood Probability: 78%**

---

## 3.2 Flood Severity

Move beyond binary flood/no-flood classification.

Suggested categories:

```text
NORMAL
WATCH
ALERT
SEVERE
EXTREME
```

Severity should be derived from the project's validated prediction/inundation methodology rather than arbitrary thresholds presented as scientific truth.

---

## 3.3 Lead Time / Forecast Window

Show when the system expects risk to become significant.

Example:

> **Expected high-risk window: 14:00–16:00**

or

> **Estimated lead time: ~2.4 hours**

Only report these values after they have been validated against held-out events.

---

## 3.4 Confidence / Uncertainty

Example:

```text
Flood probability: 78%
Confidence:         61%
Uncertainty:        HIGH
```

The platform should also explain why uncertainty increased.

Example:

```text
⚠ Rainfall observation delayed
⚠ Satellite observation partially unavailable
✓ DEM available
✓ River data available
```

---

## 3.5 Multimodal Source Agreement

This is one of the project's strongest differentiators.

Show whether different modalities are giving consistent signals.

Example:

| Data source | Signal |
|---|---|
| Rainfall | 🔴 Extreme |
| River level | 🔴 Rising |
| Satellite precipitation | 🟠 Heavy |
| Soil moisture | 🔴 Saturated |
| Terrain | 🔴 High susceptibility |

Then summarize:

> **Source agreement: 86% — strong cross-source support**

Conversely:

> **Source disagreement detected → uncertainty increased**

This directly communicates the multimodal-fusion concept to judges.

---

## 3.6 Missing-Data Impact

The system should explicitly show how missing data affects the forecast.

Example:

| Scenario | Flood probability | Confidence |
|---|---:|---:|
| All sources | 82% | 78% |
| Without rainfall | 69% | 53% |
| Without river data | 64% | 49% |
| Without satellite | 76% | 68% |

Possible UI insight:

> **River-level observations currently have the largest effect on forecast stability.**

This should be calculated from actual model experiments, not hard-coded.

---

## 3.7 Explainable Prediction

Show the major contributing features/signals.

Example:

```text
WHY IS THIS ZONE HIGH-RISK?

Rainfall              ██████████
River level            ████████
Soil moisture          ███████
Terrain susceptibility █████
Satellite signal       ████
```

The wording should remain appropriately cautious: contribution/importance, not causal proof.

---

# 4. Building-Level Flood Impact Module

## 4.1 Goal

Add a simple geospatial impact-assessment layer that takes the predicted flood extent/depth and estimates which buildings and infrastructure fall inside the affected area.

The idea is:

```text
Flood prediction
      ↓
Flood extent / depth
      ↓
Building footprints
      ↓
Spatial intersection
      ↓
Affected buildings
      ↓
Impact severity
```

---

## 4.2 Building Footprints

### Preferred hackathon path

Use an existing building-footprint dataset instead of training a new building detector from scratch.

Potential source:

- **Microsoft Global ML Building Footprints**
- Worldwide building polygons
- Suitable for a GIS overlay workflow

### Optional AI enhancement

Run a pretrained remote-sensing building segmentation/detection model on satellite imagery.

Possible tooling:

- TorchGeo / pretrained geospatial models
- Other pretrained building-segmentation models appropriate to the imagery

For the MVP, the recommended approach is:

> **Use existing building footprints for reliable spatial exposure analysis; treat AI-based building detection as an optional demo/research enhancement.**

This keeps the scope realistic.

---

# 5. Building Impact Calculation

For each building:

```text
Building footprint
          +
Flood probability
          +
Estimated water depth
          +
Inundated footprint %
          +
Expected duration
          +
Elevation relationship
          ↓
     Impact Score
```

Conceptually:

\[
Impact = f(P_{flood}, Depth, InundatedArea, Duration, Elevation)
\]

Do not present this as a scientifically validated structural-damage equation unless it has been properly calibrated and validated.

---

## 5.1 Example Building Card

```text
BUILDING B104

Impact                 CRITICAL

Flood Probability      91%
Estimated Water Depth  1.7 m
Inundated Footprint    94%
Expected Duration      5–7 h
Estimated Elevation    +1.1 m
Confidence             74%

Impact Drivers
Depth                  █████████
Duration               ███████
Flood probability      █████████
Elevation              █████
```

Suggested impact classes:

```text
0–20     Minimal
20–40    Low
40–60    Moderate
60–80    High
80–100   Critical
```

These are prototype presentation bands and must be validated/tuned for the final methodology.

---

# 6. Beyond Buildings: Infrastructure Exposure

The same spatial-overlay engine can be applied to:

### Roads
Output:

> Potentially inundated road segments

### Bridges
Output:

> Bridges intersecting the predicted flood zone

### Schools
Output:

> Schools within predicted impact areas

### Hospitals
Output:

> Critical medical facilities exposed to predicted inundation

### Settlements
Output:

> Number of settlements overlapping the predicted flood zone

The system should describe these as **exposure estimates**, not autonomous emergency decisions.

---

# 7. Risk Priority Score

A useful product-level metric is:

```text
Hazard
   ×
Exposure
   ×
Uncertainty
   ↓
Risk Priority
```

Example:

> **Risk Priority: 91/100 — Critical**

A zone with very high flood probability but little nearby infrastructure may have a lower priority than a slightly lower-probability zone containing multiple critical assets.

The exact formula should be documented and validated rather than treated as a universal disaster-management standard.

---

# 8. User Interface / UX

## Navigation

Keep the product focused. Do not create a huge collection of disconnected pages.

Recommended navigation:

```text
🌊 FloodGuard

├── 🏠 Overview
├── 🔮 Forecast
├── 🗺 Risk Map
├── 🏘 Impact
├── ⚠ Uncertainty
├── 📅 Events
└── 🧬 Data & Model
```

Persistent top-right status:

```text
● LIVE
Last updated: 12:42 PM
Data sources: 5/6
```

---

# 9. Page 1 — Overview

## Purpose

Answer:

> **What is happening right now?**

The landing dashboard should communicate the complete system in a few seconds.

### Hero section

```text
UTTARAKHAND FLOOD INTELLIGENCE

CURRENT RISK

          HIGH
          78%

↑ +12% since 3 hours ago
```

### Forecast window

```text
FORECAST WINDOW

Next 6 hours

13:00 ───── 15:00 ───── 17:00
              ▲
         HIGH-RISK WINDOW
```

### KPI cards

```text
┌─────────────┐ ┌─────────────┐
│ Flood Risk  │ │ Confidence  │
│    78%      │ │    71%      │
└─────────────┘ └─────────────┘

┌─────────────┐ ┌─────────────┐
│ High-Risk   │ │ Buildings   │
│ Zones: 12   │ │ Exposed:127 │
└─────────────┘ └─────────────┘
```

### Main map

Display:

- flood risk
- rivers
- settlements
- buildings
- roads
- critical infrastructure

### Explain the risk

```text
WHY IS RISK INCREASING?

Rainfall              ██████████
River level            ████████
Soil moisture          ███████
Terrain susceptibility █████
```

### Data quality

```text
System status: 5/6 data sources available
```

---

# 10. Page 2 — Forecast

## Purpose

Answer:

> **What is likely to happen over the next few hours?**

This is the main machine-learning showcase.

### Main chart

Use a time-series forecast:

```text
Flood Probability Forecast

100% ┤
 80% ┤                    ╭───╮
 60% ┤              ╭─────╯   ╰───
 40% ┤       ╭──────╯
 20% ┤───────╯
     └──────────────────────────────
       Now  +1h +2h +3h +4h +6h
```

### Add an uncertainty band

The graph should display:

- predicted probability
- uncertainty range/confidence interval

Conceptually:

```text
             █████ uncertainty █████

            ╭───────────╮
        ╭───╯           ╰───╮
───────╯                     ╰──────
          predicted probability
```

### Forecast summary cards

```text
Peak Risk         84%
Peak Time         15:20
Lead Time         2h 18m
Expected Severity Severe
```

Only show values produced by the actual system.

---

# 11. Page 3 — Risk Map

## Purpose

Answer:

> **Where exactly is the risk?**

This should be one of the most interactive pages.

### Map layers

```text
LAYERS

☑ Flood Probability
☑ Flood Extent
☐ Water Depth
☐ Rainfall
☐ River Level
☐ Soil Moisture
☐ Buildings
☐ Roads
☐ Critical Infrastructure
```

### Forecast time slider

```text
TIME

← NOW | +1h | +2h | +3h | +4h | +6h →
```

The map should update as the user changes time.

### Clickable zone

Example:

```text
ZONE UTH-042

Flood probability     87%
Estimated depth       1.4 m
Expected duration     4.2 h
Confidence            72%

Top factors:
Rainfall       HIGH
River level    HIGH
Soil moisture  MEDIUM
Terrain        HIGH
```

---

# 12. Page 4 — Impact

## Purpose

Answer:

> **What gets affected?**

This is where the building/infrastructure analysis becomes a first-class product feature.

### Exposure KPIs

```text
PREDICTED EXPOSURE

127 Buildings
14 Road Segments
2 Bridges
3 Schools
1 Hospital
8 Settlements
```

### Map

Display building polygons/points colored by impact:

```text
🟢 Low
🟡 Moderate
🟠 High
🔴 Critical
```

### Entity tabs

```text
[ BUILDINGS ] [ ROADS ] [ CRITICAL ASSETS ]
```

### Building click interaction

Clicking a building opens a side drawer.

Example:

```text
BUILDING B104

Impact                 CRITICAL

Flood Probability      91%
Estimated Water Depth  1.7 m
Inundated Footprint    94%
Expected Duration      5–7 h

Estimated Elevation    +1.1 m
Confidence             74%

────────────────────

Impact Drivers

Depth                  █████████
Duration               ███████
Flood probability      █████████
Elevation              █████
```

---

# 13. Page 5 — Uncertainty

## Purpose

Answer:

> **How much can we trust the prediction?**

This is the research differentiator.

### Hero metrics

```text
FORECAST RELIABILITY

          71%
       CONFIDENCE

        MEDIUM
      UNCERTAINTY
```

### Source health

```text
DATA SOURCE             STATUS

Rainfall                 ✓ Available
River sensor             ✓ Available
Satellite                ⚠ Delayed
Soil moisture            ✓ Available
DEM                      ✓ Available
Historical records       ✓ Available
```

### Missing-data experiment

```text
                 Probability   Confidence

All sources         82%           78%

No rainfall         69%           53%

No river data       64%           49%

No satellite        76%           68%
```

### Interpretation

> **Forecast stability is most sensitive to the removal of the river-level input.**

This statement should be generated from actual model ablation experiments.

---

# 14. Page 6 — Events

## Purpose

Answer:

> **How did the model perform on historical flood events?**

This page turns historical data into a visual evaluation tool.

## Flood Event Replay

Example:

```text
24 JUNE 2025
Flash Flood Event

[ ▶ PLAY EVENT ]
```

Timeline:

```text
T-6h → T-4h → T-2h → T-1h → EVENT
```

As the timeline plays:

- map updates
- predicted risk evolves
- predicted extent evolves
- uncertainty evolves

### Predicted vs observed

Show side-by-side or toggle between:

```text
PREDICTED
vs
OBSERVED
```

### Performance metrics

Once properly evaluated:

```text
Prediction Performance

Precision       0.XX
Recall           0.XX
F1 Score         0.XX
AUROC            0.XX

Average Lead Time
XX minutes
```

Also show:

- false alarms
- missed events
- successful detections
- calibration/reliability where available

Do not invent historical lead-time or performance numbers for the demo.

---

# 15. Page 7 — Data & Model

## Purpose

Answer:

> **Where did this prediction come from?**

This page is mainly for judges and technical reviewers.

### Pipeline visualization

```text
SATELLITE
    │
RAINFALL ───┐
RIVER ──────┤
SOIL ───────┼──► MULTIMODAL FUSION
DEM ────────┤
HISTORY ────┘
                 │
                 ▼
          FLOOD PREDICTION
                 │
        ┌────────┴────────┐
        ▼                 ▼
      EXTENT         UNCERTAINTY
        │                 │
        └────────┬────────┘
                 ▼
            IMPACT ENGINE
                 │
       Buildings / Roads /
       Bridges / Hospitals
```

### Show

- data source names
- preprocessing stages
- feature groups
- model architecture
- validation metrics
- data freshness
- missing-data statistics
- model version

Do not turn this page into a wall of library names.

---

# 16. Mobile / PWA Experience

Do not simply shrink the desktop dashboard onto mobile.

## Web/PWA

Target user:

> Disaster-management analyst / authority / researcher

Features:

- full map
- layer controls
- forecast graphs
- impact analysis
- uncertainty diagnostics
- historical replay
- detailed data/model page

## Mobile

Target user:

> Field user / monitored-area user

Keep it simple.

Example:

```text
🔴 HIGH FLOOD RISK

Monitored Area:
Rishikesh Sector 4

Risk                  82%
Expected onset        ~2h
Confidence            71%

────────────────────

Affected Assets

🏠 27 Buildings
🛣 2 Roads
🌉 1 Bridge

────────────────────

[ OPEN MAP ]

[ VIEW DETAILS ]
```

Also show:

> **Data quality warning:** River sensor unavailable

The mobile experience should focus on **current status, location, affected assets, and data reliability**.

---

# 17. Cross-Page Interaction Flow

The pages should not feel like separate dashboards.

Create a guided drill-down.

## Example Demo Journey

```text
OVERVIEW
   │
   │  "High risk — 78%"
   ↓
FORECAST
   │
   │  "Peak risk 84% in 2h"
   ↓
RISK MAP
   │
   │  Select Zone UTH-042
   ↓
IMPACT
   │
   │  "23 buildings exposed"
   ↓
BUILDING B104
   │
   │  "91% flood probability"
   ↓
UNCERTAINTY
   │
   │  "Confidence 74%"
   │  "Satellite data delayed"
   ↓
DATA / MODEL
   │
   │  Show source + fusion pipeline
   ↓
EVENTS
      "Compare with historical event"
```

This creates a story:

> **Predict → Locate → Explain → Quantify → Validate**

---

# 18. Optional Counterfactual Sensor Reliability View

This is one of the strongest research-oriented additions.

Show:

```text
WHAT HAPPENS IF A DATA SOURCE DISAPPEARS?

                         Probability   Confidence

ALL SOURCES                  82%           78%

WITHOUT RAINFALL             71%           55%

WITHOUT SATELLITE            79%           68%

WITHOUT RIVER DATA            64%           49%
```

Then:

> **Most sensitive modality: River-level observations**

This should be calculated through real ablation experiments.

---

# 19. Optional Building-Level Asset Impact Summary

For a selected region:

```text
ZONE UTH-042

Buildings
──────────────
Critical       6
High           11
Moderate       8
Low            13

Roads
──────────────
High exposure  3
Moderate       5

Critical Assets
──────────────
Hospital       1
School         2
Bridge         1
```

This provides a quick executive view.

---

# 20. Optional “Why Is This Area Risky?” Panel

For a selected location:

```text
WHY IS THIS AREA RISKY?

Rainfall                 HIGH
River level              HIGH
Soil moisture             HIGH
Terrain susceptibility    HIGH
Satellite precipitation  MEDIUM

Source agreement: 86%
Confidence: 72%
```

This makes the model interpretable without claiming causal reasoning.

---

# 21. Optional Risk Comparison

Allow the analyst to compare two zones.

```text
ZONE A                         ZONE B

Flood probability  88%        Flood probability  74%
Confidence          76%        Confidence          61%
Buildings exposed   19         Buildings exposed   47
Roads exposed         2        Roads exposed         6
Critical assets       0        Critical assets       3

Priority             HIGH      Priority            CRITICAL
```

This makes the **hazard vs exposure** distinction visible.

---

# 22. Suggested Technical Stack

The exact stack can change depending on what the team already knows.

## Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS
- MapLibre GL JS / Mapbox-compatible mapping
- Recharts / ECharts
- PWA support

## Backend

- FastAPI and/or Spring Boot
- PostgreSQL + PostGIS
- Redis / background jobs where needed

## ML

Possible model families:

- Gradient boosting
- Random Forest
- XGBoost / LightGBM
- LSTM / temporal models
- CNN / raster models
- multimodal feature fusion
- probabilistic or ensemble uncertainty estimation

Use the simplest model that performs well enough for the available data. Do not add deep learning solely for presentation.

## Geospatial

- GeoPandas
- Rasterio
- Shapely
- PostGIS
- GDAL ecosystem

## Optional geospatial AI

- TorchGeo
- pretrained building segmentation/detection model

---

# 23. Recommended ML Output Contract

Each prediction should ideally return something close to:

```json
{
  "location_id": "UTH-042",
  "timestamp": "2026-10-08T14:00:00",
  "flood_probability": 0.78,
  "severity": "HIGH",
  "prediction_interval": {
    "lower": 0.66,
    "upper": 0.87
  },
  "confidence": 0.71,
  "source_agreement": 0.86,
  "estimated_lead_time_hours": 2.4,
  "data_quality": {
    "rainfall": "available",
    "river": "available",
    "satellite": "delayed",
    "soil_moisture": "available",
    "dem": "available"
  }
}
```

The actual uncertainty representation should match the selected model/calibration method.

---

# 24. Recommended Impact Output Contract

Example:

```json
{
  "asset_id": "B104",
  "asset_type": "building",
  "zone_id": "UTH-042",
  "flood_probability": 0.91,
  "estimated_water_depth_m": 1.7,
  "inundated_footprint_percent": 94,
  "expected_duration_hours": 5.5,
  "confidence": 0.74,
  "impact_score": 82,
  "impact_class": "CRITICAL"
}
```

This is a product-level schema; it should be adjusted once the actual flood-depth and exposure methodology is finalized.

---

# 25. What NOT to Claim

The system should remain a **decision-support / forecasting and exposure platform**.

Avoid claiming:

- exact structural damage
- exact monetary loss
- exact casualty prediction
- autonomous evacuation decisions
- guaranteed flood arrival times
- clinically/emergency-authoritatively certified outputs
- causality from feature importance alone

Better wording:

- predicted
- estimated
- potentially affected
- exposed
- model confidence
- forecast uncertainty
- monitoring priority

---

# 26. MVP Scope for a Hackathon

Do not attempt to build everything at once.

## Tier 1 — Must Have

### Data
- 3–6 meaningful modalities
- cleaned and normalized
- aligned by time and geography

### ML
- baseline model
- multimodal model
- uncertainty estimation
- validation on held-out data

### Product
- Overview
- Forecast
- Risk Map
- Impact

### Impact
- building footprints
- spatial intersection
- affected-building count
- basic impact severity

---

# 27. Tier 2 — Strong Differentiators

Add:

- Uncertainty page
- source agreement
- missing-data experiments
- water-depth view
- exposure layer for roads and bridges
- critical infrastructure
- time-slider map

---

# 28. Tier 3 — Showcase Features

Add only if the core system works:

- historical event replay
- predicted vs observed comparison
- counterfactual sensor ablation
- building-height/floor approximation
- zone comparison
- automated report generation
- mobile/PWA field view

---

# 29. Recommended Demo Sequence

A strong live demo could be:

### Step 1
Open **Overview**

> “The system currently detects high flood risk.”

### Step 2
Open **Forecast**

> “Risk is expected to peak in approximately X hours.”

### Step 3
Open **Risk Map**

> “This is where the model expects the highest-risk area.”

### Step 4
Turn on **Buildings**

> “Now we translate the flood prediction into physical exposure.”

### Step 5
Click a building

> “This building has X% predicted flood probability and Y% estimated footprint inundation.”

### Step 6
Open **Uncertainty**

> “But here's the important part: the model is not blindly confident. Satellite data is delayed, so uncertainty increases.”

### Step 7
Open **Events**

> “Finally, we replay historical events and compare what the model predicted against what actually happened.”

That is a clean **2–4 minute judge demo**.

---

# 30. Final Product Definition

The project can be described as:

> **An uncertainty-aware multimodal flash-flood intelligence platform that fuses environmental observations, predicts flood risk and lead time, maps potential inundation, and translates the prediction into building and infrastructure exposure.**

### The three intelligence layers

```text
┌────────────────────────────────────────────┐
│  LAYER 1 — HAZARD                          │
│  Will flooding occur?                      │
│                                            │
│  Multimodal flood prediction + uncertainty │
└──────────────────────┬─────────────────────┘
                       ↓
┌────────────────────────────────────────────┐
│  LAYER 2 — INUNDATION                      │
│  Where/how deep could it be?               │
│                                            │
│  Flood extent + depth + forecast window    │
└──────────────────────┬─────────────────────┘
                       ↓
┌────────────────────────────────────────────┐
│  LAYER 3 — EXPOSURE & IMPACT               │
│  What could be affected?                   │
│                                            │
│  Buildings + roads + bridges + critical    │
│  infrastructure                            │
└────────────────────────────────────────────┘
```

## One-line pitch

> **“We don't just predict where a flash flood may occur — we quantify uncertainty, estimate inundation, and translate the forecast into building- and infrastructure-level exposure.”**

---

# 31. Design Principles

1. **Map-first, not chart-first.**
2. **Every prediction should have uncertainty.**
3. **Every risk should be spatially explorable.**
4. **Every important output should be traceable to data sources.**
5. **Do not overload the user with ML jargon.**
6. **Use progressive disclosure: overview first, details on click.**
7. **Desktop is for analysis; mobile is for field awareness.**
8. **Do not present prototype scores as scientifically validated damage predictions.**
9. **Never hard-code impressive metrics.**
10. **Build the demo around one memorable end-to-end story.**

---

# 32. The Core Wow Factor

The project should make the judge experience this progression:

```text
                    FLOOD RISK
                        ↓
                 "82% probability"
                        ↓
                  WHERE?
                        ↓
                  "This zone"
                        ↓
                 WHEN?
                        ↓
                  "In ~2h"
                        ↓
              HOW CERTAIN?
                        ↓
                "Confidence 71%"
                        ↓
                 WHAT GETS HIT?
                        ↓
             "127 buildings + roads"
                        ↓
                HOW BAD?
                        ↓
           "41 high/critical assets"
                        ↓
               WHY THIS RISK?
                        ↓
       "Rain + river + soil + terrain"
                        ↓
              CAN WE TRUST IT?
                        ↓
           "Show uncertainty + ablation"
```

---

## Final UI Philosophy

The system should feel like one continuous intelligence workflow rather than a collection of dashboards:

> **Situation → Forecast → Location → Impact → Uncertainty → Validation**

The most important hackathon moment is the transition from a flood-risk heatmap to a building-level exposure view while keeping uncertainty visible. That is where the project moves from **“another flood prediction model”** to a much more complete **flood intelligence platform**.
