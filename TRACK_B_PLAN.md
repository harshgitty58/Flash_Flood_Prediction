# PRAHAR: Checklist (2026-10-15)

Order agreed with the user: **A** (resume previous tasks) → **B** (home page imagery) → **C** (Track B).

## A. Previous tasks (resumed on "let's play")
- [~] A1. (284/744, running) MHA daily situation reports, 27 Aug 2023 → 2025 (744 PDFs), downloading in the background (`scripts/fetch_mha_sitreps.py`; resumes where it stopped).
- [x] A2. Parser written (`scripts/parse_mha_sitreps.py`; final run when A1 finishes). Parse them into two tables:
  - Uttarakhand **state-level daily damage** (dead / injured / missing / houses, plus cause);
  - IMD **"significant rainfall in last 24 h"** districts (rainfall range in cm and district names).
- [ ] A3. Use them in external validation (Uttarakhand damage days) and as official rain evidence for ungauged districts. **Ask before any alert-logic change.**
- [ ] A4. RTI to USDMA for SEOC daily reports, Jun–Oct 2024 and 2025 (the user files it; draft given). Ingest the reply when it arrives.

## B. Home page imagery
- [x] B1. A full-screen hero image plus image bands stacked further down, darkened so the text stays readable.
- [x] B2. (6 cloud-free Sentinel-2 scenes, `scripts/fetch_home_imagery.py`) Sources: **Sentinel-2 satellite scenes** of Uttarakhand flood sites (Dharali Aug 2025, Kedarnath valley, Joshimath / Alaknanda, Ganga at Haridwar). These are free Copernicus data. Add **Wikimedia Commons** landscape photos only where the licence allows. **No images of victims** (Track B rule). An attribution line goes in the footer.
- [x] B3. Images are compressed WebP (≤ 300 KB each) and lazy-loaded, so page load stays fast.

## C. Track B: "Mapping Flood Damage from Space" (Multimodal AI Hackathon 2026)
**Scoring:** flood and damage mapping 30 % · AI component 25 % · cut-off settlements 20 % · report, Q&A and honesty 15 % · dashboard and situation report 10 %. Judged live on areas and dates chosen by the judges.

**Allowed inputs only:**
- Sentinel-1 and Sentinel-2;
- Copernicus DEM (GLO-30);
- pre-event OSM (ohsome API, snapshot before the event);
- Kuro Siwo / Sen1Floods11 (training).

Copernicus EMS / UNOSAT maps and post-event OSM may be used **only for checking**. Using them as inputs means disqualification.

**What we already have that carries over:**
- impact engine (zones × hazard), audit discipline, MapLibre dashboard, glass UI, tiling;
- FastAPI backend, report generation, the "honest limits" sections;
- DEM handling and river-distance logic.

**What does NOT carry over:**
- Microsoft building footprints (not an allowed input → use pre-event OSM buildings);
- the AWS Terrarium DEM (→ Copernicus GLO-30);
- ERA5, gauges and the IMD labels (not satellite inputs);
- Uttarakhand-only data paths. The new system must work for any area and date.

| # | Module | Method | Score weight |
|---|---|---|---|
| C1 | **Input layer:** area (bbox) + flood date → data | STAC search: Sentinel-1 GRD/RTC (same relative orbit, before/after ≈ 12 days apart), Sentinel-2 L2A (cloud-filtered), Copernicus GLO-30, ohsome snapshot before the event (buildings, roads, bridges, settlements, hospitals) | prerequisite |
| C2 | **Where did it hit?** | S1 change detection (log-ratio of after/before VV/VH, Otsu threshold, terrain/shadow mask from DEM slope, HAND mask) + S2 NDWI/MNDWI change when cloud-free + debris index (brightness/NDVI loss) | 30 % |
| C3 | **AI component: flood segmentation** | U-Net (light, e.g. ResNet-18 encoder) on **Kuro Siwo** (multi-temporal S1 pairs), Sen1Floods11 optional. Evaluated on **held-out Himalayan scenes** (Uttarakhand 2025, Trishuli 2026) with IoU / F1 against our C2 and an independent check | 25 % |
| C4 | **What was damaged?** | Overlay pre-event OSM buildings, roads and bridges on the flood/debris mask; per-object hit / near-miss, with counts per settlement | (in 30 %) |
| C5 | **Who is cut off?** | OSM road graph (networkx). Remove flooded edges and bridges; settlements with no path to the nearest town or hospital are "cut off"; report path-length increase for the rest | 20 % |
| C6 | **Situation report** | One-page PDF/HTML auto-generated from system outputs (every number comes from the maps, nothing typed by hand). Optional LLM copilot (English + Nepali) that only reads system numbers | 10 % (+ could be the AI component) |
| C7 | **Bonus: flood path** | D8 flow routing on GLO-30 from any upstream point; list settlements along the path | bonus |
| C8 | **Case study** | Trishuli Aug 2026 (event 26 Aug 2026), compared against EMSR927 *for checking only*: IoU, precision / recall of flooded area, damaged-building agreement | part of the report |
| C9 | **Dashboard** | New "Space" mode in the existing app: pick area + date → layers (flood / debris, damaged objects, cut-off settlements, flood path) + "Generate sitrep" | 10 % |
| C10 | **Deliverables** | README run guide · report ≤ 6 pages with a limitations section (S1/S2 revisit, radar layover/shadow in steep valleys, OSM completeness, debris vs. wet soil) · 3-min video · required attributions · Kuro Siwo citation (Bountos et al. 2024) | 15 % |

**Decisions needed from the user before C:**
1. Is Track B the submission target? It's a separate system with a Nepal case study and allowed-inputs-only rules, so PRAHAR's Uttarakhand nowcasting stays as the course project.
2. Accounts: a free Copernicus Data Space registration may be needed for S1/S2 downloads. Microsoft Planetary Computer / Element84 Earth Search STAC work without one.
3. Compute: training the U-Net on Kuro Siwo needs a GPU (a Colab T4 is fine). A CPU fallback would be a small model on a subset.

## Progress log (2026-10-15)
- **C1 input layer: done** (`src/space/data.py`), all keyless:
  - Sentinel-1 RTC via Planetary Computer, with same-orbit before/after pairs;
  - Sentinel-2 via Earth Search;
  - Copernicus GLO-30 on AWS;
  - pre-event OSM via ohsome `elementsFullHistory/geometry`, keeping the versions valid at the snapshot date (`/elements/geometry` is blocked for anonymous use).
- **C2 rule-based detection: built, NOT reliable in mountains** (`src/space/flood.py`, UN-SPIDER recommended practice). Dharali test (5 Aug 2025, S1 track 129, after image 4.5 h post-event):
  - the UN-SPIDER 5 % slope mask removes 99.6 % of the valley. User chose ESA layover/shadow geometry instead, which leaves 262.8 km² analysable;
  - the 1.25 ratio then flags 40.9 km² "water" and 22.6 km² "debris", and detection is no denser at the Dharali fan than scene-wide. A 12-day monsoon pair in steep terrain is dominated by wet-slope and vegetation change;
  - a published HAND exclusion value could not be verified (GFM gives none; the Twele et al. 2016 full text is closed), so none is applied.
- **Next:**
  - (a) the AI model (Kuro Siwo, Colab GPU) is now the primary flood/debris detector, with rules kept as a baseline;
  - (b) a valley constraint is still needed: options in chat;
  - (c) C4 damage, C5 cut-off, C6 sitrep, C9 dashboard.
- **C2 corridor (user choice):** detection is limited to 200 m of pre-event OSM waterways (Uttarakhand HC corridor). Dharali: 70 km² corridor; the rule baseline still flags 13.1 km² "water". It stays a baseline; the AI model will be the detector.
- **C3 AI:** `notebooks/trackB_train_floodseg_colab.ipynb`. U-Net ResNet-34 with 7 channels (post + 2 pre S1 VV/VH in dB, relative DEM), trained on the Kuro Siwo official train split, streamed from Hugging Face, tested on the official unseen-event test split, exported as ONNX. **User runs it on Colab T4** and puts `prahar_floodseg.zip` in `models/space/`.
- **C4 + C5: done** (`src/space/impact.py`, runner writes `results/space/<name>/`). Dharali with the baseline mask:
  - 69/502 buildings, 40/112 roads and 3/16 bridges hit;
  - 8 settlements cut off from the AOI exits (incl. Harsil, consistent with reports), 2 still connected.
- **Next:** C3 inference module (ONNX, CPU) once the weights arrive · C6 situation report · C7 flood-path bonus · C8 Trishuli 2026 vs EMSR927 · C9 dashboard Space mode · A3 MHA integration (2025 OCR running).
