"""Space mode — one-page situation report, generated only from the system's own outputs (no hand-typed numbers).

Reads results/space/<name>/{summary.json, cutoff.json} and models/space/floodseg_meta.json and writes
results/space/<name>/sitrep.md and sitrep.html.  Run: python -m src.space.report --name dharali
"""
import argparse
import html
import json

from src.config import PROJECT_ROOT

ATTRIB = ["Contains modified Copernicus Sentinel data 2025–2026.",
          "Produced using Copernicus WorldDEM-30 © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018 provided under COPERNICUS by the European Union and ESA; all rights reserved.",
          "© OpenStreetMap contributors (pre-event snapshot via the ohsome API).",
          "Training data: Kuro Siwo (Bountos et al., NeurIPS 2024, CC BY 4.0)."]


def build(name: str) -> str:
    d = PROJECT_ROOT / "results/space" / name
    s = json.loads((d / "summary.json").read_text())
    c = json.loads((d / "cutoff.json").read_text())
    m = json.loads((PROJECT_ROOT / "models/space/floodseg_meta.json").read_text()) if (PROJECT_ROOT / "models/space/floodseg_meta.json").exists() else {}
    f, dm = s["flood"], s["damage"]
    cut = [r for r in c["settlements"] if r["status"] == "CUT OFF"]
    longer = [r for r in c["settlements"] if r["status"] == "longer route"]
    flood_km2 = f.get("ai_flood_km2_corridor", f.get("water_km2"))
    L = [f"# Situation report — {name.title()} (event {s['event_utc'][:16]} UTC)", "",
         f"*Generated automatically by PRAHAR Space mode from Sentinel-1 radar, Copernicus DEM and pre-event OpenStreetMap ({s['osm_snapshot']}). Every number below comes from the system's maps.*", "",
         "## Where did the flood hit?",
         f"- Detector: **{s.get('detector', 'rule baseline')}**.",
         f"- Flooded area inside the 200 m river corridor: **{flood_km2} km²**" + (f" (whole area: {f.get('ai_flood_km2_all')} km²)" if "ai_flood_km2_all" in f else "") + ".",
         f"- Radar pairs used (same orbit): " + "; ".join(f"track {p['orbit']} {p['state']} {p['before_t'][:10]} → {p['after_t'][:16]}" for p in s["s1_pairs"]) + ".",
         f"- Not analysable: radar layover/shadow on {f.get('hidden_all_orbits_km2')} km²; permanent water {f.get('permanent_water_km2')} km².", "",
         "## What was damaged? (pre-event OSM objects on flooded pixels)",
         f"- Buildings: **{dm['buildings']['hit']} of {dm['buildings']['total']}**",
         f"- Road segments: **{dm['roads']['hit']} of {dm['roads']['total']}** · Bridges: **{dm['bridges']['hit']} of {dm['bridges']['total']}**", "",
         f"## Who is cut off? (road connection to nearest {c['destination']})",
         f"- **{len(cut)} settlements cut off**: " + (", ".join(sorted({r['name'] for r in cut if r['name']})) or "none") + ".",
         f"- {len(longer)} reachable only by a longer route; {c['counts'].get('connected', 0)} still connected; {c['counts'].get('not connected before', 0)} had no mapped road link even before the flood.", ""]
    if m:
        t = m.get("test_scores_unseen_events", {})
        L += ["## Model reliability",
              f"- U-Net trained on Kuro Siwo; on unseen test events: flood precision {t.get('flood_precision')}, recall {t.get('flood_recall')}, F1 {t.get('flood_f1')}, IoU {t.get('iou_flood')}.",
              "- Read as: when it says 'flooded' it is right about half the time; it misses many flooded pixels.", ""]
    L += ["## Limitations (read before acting)",
          "- Sentinel-1 revisits every 6–12 days: this maps what the satellite saw, not the moment of the flood, and cannot warn in advance.",
          "- Steep Himalayan slopes cause radar layover/shadow; narrow gorges and debris under forest can be missed.",
          "- OSM completeness varies; unmapped buildings and roads cannot be counted. Damage = 'on a flooded pixel', not structural damage.",
          "- Educational prototype — verify on the ground before operational use.", "",
          "*" + " ".join(ATTRIB) + "*"]
    md = "\n".join(L)
    (d / "sitrep.md").write_text(md, encoding="utf-8")
    body = "".join(f"<h2>{html.escape(x[3:])}</h2>" if x.startswith("## ") else f"<h1>{html.escape(x[2:])}</h1>" if x.startswith("# ")
                   else f"<li>{html.escape(x[2:]).replace('**', '')}</li>" if x.startswith("- ") else f"<p>{html.escape(x).replace('*', '')}</p>" if x else "" for x in L)
    (d / "sitrep.html").write_text(f"<!doctype html><meta charset=utf-8><title>Sitrep {name}</title><style>body{{font:14px/1.45 system-ui;max-width:780px;margin:24px auto;color:#111}}h1{{font-size:20px}}h2{{font-size:15px;margin:14px 0 4px}}li{{margin:2px 0}}p{{font-size:12px;color:#444}}</style>{body}", encoding="utf-8")
    return md


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--name", required=True)
    print(build(ap.parse_args().name))
