# FloodGuard — Build Plan & UI Scheme

Source spec: `flood_intelligence_platform.md`. This file is the executable plan.

## 0. Ground rules (from the spec, non-negotiable)
- Every number on screen comes from `data/` or `results/` via the export script. No hard-coded metrics.
- The app runs in **REPLAY mode** on real held-out predictions (XGBoost, test split), not a fake "LIVE" feed.
- Missing modules (conformal uncertainty, buildings, depth) render an honest "pending" state, never placeholder numbers.
- Wording: *predicted / estimated / exposed / model confidence*. Never "damage", "will flood", "guaranteed".

## 1. UI scheme — "Monsoon Night"
Inspiration: the editorial disaster hero (giant condensed uppercase type, outlined second line, pulsing
dashed-ring hotspots on a dark photo) + dark hydromet ops consoles (terrain map, red-orange heat ramps).

| Token | Value | Use |
|---|---|---|
| `--bg` | `#06080c` | page |
| `--panel` | `#0d1117` / 70% + blur | glass panels over map |
| `--line` | `#1f2937` | hairlines |
| `--ink` / `--mute` | `#e8edf3` / `#8b98a9` | text |
| `--water` | `#38bdf8` | rivers, data, focus ring |
| Risk ramp | NORMAL `#3ddc97` · WATCH `#f5d547` · ALERT `#ff9f1c` · SEVERE `#ff4d2e` · EXTREME `#e0115f` | tiers, markers, heat |

Type: **Anton** (display, uppercase, outlined variant) · **Inter** (UI) · **JetBrains Mono** (numbers, IDs, timestamps).

Signature elements
1. Pulsing dashed-ring hotspot markers (from the Japan hero) — size = probability, colour = tier.
2. Dark terrain map (CARTO dark-matter + AWS Terrarium hillshade) — the Himalaya *is* the hero visual.
3. Mono "instrument" readouts: `P 0.66 · CONF — · 05 SEP 2026 19:00 IST`.
4. Glass side drawer for progressive disclosure (overview → click → detail).
5. Status pill top-right: `● REPLAY · 05 Sep 2026 19:00 · Sources 4/6`.

## 2. Information architecture
```
/            Landing (sell): hero map + "FLASH FLOODS DON'T WAIT / UTTARAKHAND",
             the question chain (Will → When → Where → How sure → What's hit), 3 layers, CTA
/app         Console, left icon rail:
  overview   current risk hero, KPI cards, map, "why" drivers, source health
  forecast   probability timeline around replay time (+ uncertainty band when Phase 4 lands)
  map        full map, layer toggles, time scrubber, zone drawer
  impact     exposure (pending footprints → empty state with ingest instructions)
  uncertainty source health + modality ablation (real Exp A–E fusion results)
  events     historical inventory timeline + replay of a held-out window
  model      pipeline diagram, metrics table, feature importance, data freshness
/field       Mobile card view (Tier 3)
```

## 3. Stack
Vite + React + TypeScript + Tailwind v4 · MapLibre GL · Recharts · react-router. Static build, no backend:
`scripts/export_frontend_data.py` writes JSON to `web/public/data/`. FastAPI comes later only if live inference is needed.

## 4. Data contract (exported JSON)
- `stations.json` — station, district, lat, lon, kind (rain/river)
- `snapshot.json` — replay time + per-station `{p, tier, observed, has_data}`
- `timeline.json` — hourly max/mean regional probability ±48 h around replay time
- `model.json` — model comparison, fusion ablation (A–E), grouped feature importance
- `events.json` — flood inventory records + landslide density by district

## 5. Build phases
| # | Deliverable | Status |
|---|---|---|
| B1 | Export script + JSON contract | done |
| B2 | Scaffold, design tokens, app shell (rail, status pill) | done |
| B3 | Landing page | done |
| B4 | Overview + Risk Map (real replay data) | done |
| B5 | Data & Model + Uncertainty (ablation) pages | done |
| B6 | Forecast + Events pages | basic version done; event replay next |
| B7 | Phase 4 hooks: conformal bands, SHAP drivers → replace "pending" states | after Phase 4 |
| B8 | Impact: OSM/Microsoft footprints for 2–3 towns (Rudraprayag, Uttarkashi, Dehradun) + overlay | next |
| B9 | /field mobile view, PWA manifest | Tier 3 |

## 6. Demo story (2–4 min)
Landing → Open console → Overview shows replay of 05 Sep 2026 cluster (Rudraprayag/Uttarkashi) →
Map: click Sonprayag → drawer with drivers → Uncertainty: "removing landslide/flood-history inputs drops
ROC-AUC from 0.93 to 0.36" → Model page: honest validation vs test gap.
