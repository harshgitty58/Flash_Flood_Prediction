import * as maplibregl from 'maplibre-gl'
import { useEffect, useRef } from 'react'
import { PageHead, Panel, Stat } from '../components/ui'
import { useData } from '../lib/data'

type FC = GeoJSON.FeatureCollection
type Score = { precision: number; recall: number; f1: number; iou: number }
type Settlement = { name: string | null; place: string; lon: number; lat: number; before_km: number | null; after_km: number | null; status: string }
export type SpaceData = {
  name: string; event_utc: string; bbox: [number, number, number, number]; detector: string; osm_snapshot: string
  s1_pairs: { orbit: number; state: string; before_t: string; after_t: string }[]
  flood: Record<string, number>; damage: Record<'buildings' | 'roads' | 'bridges', { total: number; hit: number }>
  cutoff: { destination: string; counts: Record<string, number>; settlements: Settlement[] }
  model: { arch?: string; flood_threshold?: number; test_scores_unseen_events?: { flood_tuned?: Score; any_water?: Score; flood_argmax?: Score } }
  layers: { flood: FC; buildings_hit: FC; roads: FC; bridges: FC }
  sitrep: string
  debris?: { summary: { km2: number; damage: Record<'buildings' | 'roads' | 'bridges', { total: number; hit: number }>; cutoff: Record<string, number> }; cutoff: { settlements: Settlement[] }; polygons: FC; buildings_hit: FC; roads: FC } | null
}

const SAT = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
const STATUS_COLOR: Record<string, string> = { 'CUT OFF': '#e0115f', 'longer route': '#ff9f1c', connected: '#3ddc97', 'not connected before': '#8fa79a' }

function SpaceMap({ d }: { d: SpaceData }) {
  const el = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!el.current) return
    const [w, s, e, n] = d.bbox
    const m = new maplibregl.Map({
      container: el.current, bounds: [[w, s], [e, n]], fitBoundsOptions: { padding: 20 }, attributionControl: { compact: true },
      style: { version: 8, sources: { sat: { type: 'raster', tiles: [SAT], tileSize: 256, attribution: 'Imagery © Esri · Contains modified Copernicus Sentinel data · © OpenStreetMap contributors' } },
               layers: [{ id: 'sat', type: 'raster', source: 'sat', paint: { 'raster-brightness-max': 0.75 } }] },
    })
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
    m.on('load', () => {
      if (d.debris) {   // low-confidence rule layer, drawn under the AI floodwater
        m.addSource('deb', { type: 'geojson', data: d.debris.polygons })
        m.addLayer({ id: 'deb', type: 'fill', source: 'deb', paint: { 'fill-color': '#b5651d', 'fill-opacity': 0.45 } })
        m.addSource('deb-bld', { type: 'geojson', data: d.debris.buildings_hit })
        m.addLayer({ id: 'deb-bld', type: 'line', source: 'deb-bld', paint: { 'line-color': '#ffb347', 'line-width': 1.5 } })
        m.addSource('deb-roads', { type: 'geojson', data: d.debris.roads })
        m.addLayer({ id: 'deb-roads', type: 'line', source: 'deb-roads', paint: { 'line-color': '#ffb347', 'line-width': 2.5, 'line-dasharray': [2, 1.5] } })
      }
      m.addSource('flood', { type: 'geojson', data: d.layers.flood })
      m.addLayer({ id: 'flood', type: 'fill', source: 'flood', paint: { 'fill-color': ['match', ['get', 'class'], 'flood', '#1e90ff', '#0b3d91'], 'fill-opacity': 0.6 } })
      m.addSource('roads', { type: 'geojson', data: d.layers.roads })
      m.addLayer({ id: 'roads', type: 'line', source: 'roads', paint: { 'line-color': ['case', ['get', 'hit'], '#ff9f1c', '#ffffff'], 'line-width': ['case', ['get', 'hit'], 3, 1], 'line-opacity': ['case', ['get', 'hit'], 1, 0.45] } })
      m.addSource('bridges', { type: 'geojson', data: d.layers.bridges })
      m.addLayer({ id: 'bridges', type: 'line', source: 'bridges', paint: { 'line-color': ['case', ['get', 'hit'], '#e0115f', '#f5d547'], 'line-width': 4 } })
      m.addSource('bld', { type: 'geojson', data: d.layers.buildings_hit })
      m.addLayer({ id: 'bld', type: 'fill', source: 'bld', paint: { 'fill-color': '#ff2d2d', 'fill-opacity': 0.9 } })
      m.addLayer({ id: 'bld-line', type: 'line', source: 'bld', paint: { 'line-color': '#ffffff', 'line-width': 1 } })
      const pts: FC = { type: 'FeatureCollection', features: d.cutoff.settlements.map(r => ({ type: 'Feature', geometry: { type: 'Point', coordinates: [r.lon, r.lat] }, properties: { ...r } })) }
      m.addSource('pl', { type: 'geojson', data: pts })
      m.addLayer({ id: 'pl', type: 'circle', source: 'pl', paint: { 'circle-radius': 7, 'circle-color': ['match', ['get', 'status'], 'CUT OFF', STATUS_COLOR['CUT OFF'], 'longer route', STATUS_COLOR['longer route'], 'connected', STATUS_COLOR.connected, STATUS_COLOR['not connected before']], 'circle-stroke-color': '#000', 'circle-stroke-width': 1.5 } })
      m.addLayer({ id: 'pl-txt', type: 'symbol', source: 'pl', layout: { 'text-field': ['get', 'name'], 'text-size': 12, 'text-offset': [0, 1.2], 'text-anchor': 'top', 'text-font': ['Open Sans Semibold'] }, paint: { 'text-color': '#fff', 'text-halo-color': '#000', 'text-halo-width': 1.5 } })
      m.on('click', 'pl', (ev: maplibregl.MapLayerMouseEvent) => {
        const p = ev.features?.[0]?.properties as Record<string, unknown> | undefined
        if (p) new maplibregl.Popup().setLngLat(ev.lngLat).setText(`${p.name ?? 'Settlement'}: ${p.status} (road to ${d.cutoff.destination}: ${p.before_km ?? '—'} km before, ${p.after_km ?? 'no route'} after)`).addTo(m)
      })
    })
    return () => m.remove()
  }, [d])
  return <div ref={el} className="h-[520px] w-full overflow-hidden rounded-xl" />
}

const f = (v?: number, d = 2) => (v == null ? '—' : v.toFixed(d))

export default function Space() {
  const d = useData<SpaceData>('space')
  if (!d) return null
  const t = d.model.test_scores_unseen_events
  const cut = d.cutoff.settlements.filter(s => s.status === 'CUT OFF')
  const flooded = d.flood.ai_flood_km2_corridor ?? d.flood.water_km2
  return (
    <div className="mx-auto max-w-6xl p-6">
      <PageHead kicker="Space mode · Track B" title={`${d.name[0].toUpperCase()}${d.name.slice(1)} flood from space`}
        question="Where did the flood hit, what was damaged, and who is cut off? From Sentinel-1 radar, the Copernicus DEM and pre-event OpenStreetMap only." />
      <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
        <Stat label="Flooded (200 m river corridor)" value={`${f(flooded, 1)} km²`} sub={d.detector} color="#4fb3f0" />
        <Stat label="Buildings hit" value={`${d.damage.buildings.hit}/${d.damage.buildings.total}`} sub={`OSM as of ${d.osm_snapshot}`} color="#ff2d2d" />
        <Stat label="Road segments hit" value={`${d.damage.roads.hit}/${d.damage.roads.total}`} sub={`bridges ${d.damage.bridges.hit}/${d.damage.bridges.total}`} color="#ff9f1c" />
        <Stat label="Settlements cut off" value={cut.length} sub={`no road to ${d.cutoff.destination}`} color="#e0115f" />
        <Stat label="AI flood F1 (unseen events)" value={f(t?.flood_tuned?.f1)} sub={`precision ${f(t?.flood_tuned?.precision)} · recall ${f(t?.flood_tuned?.recall)}`} color="var(--color-brand)" />
      </div>

      {d.debris && <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label="Possible debris (rule, low confidence)" value={`${f(d.debris.summary.km2, 1)} km²`} sub="radar change, not validated" color="#b5651d" />
        <Stat label="Buildings on possible debris" value={`${d.debris.summary.damage.buildings.hit}/${d.debris.summary.damage.buildings.total}`} sub="outlined amber on the map" color="#ffb347" />
        <Stat label="Roads on possible debris" value={`${d.debris.summary.damage.roads.hit}/${d.debris.summary.damage.roads.total}`} sub={`bridges ${d.debris.summary.damage.bridges.hit}`} color="#ffb347" />
        <Stat label="Cut off if debris blocks roads" value={d.debris.summary.cutoff['CUT OFF'] ?? 0} sub={d.debris.cutoff.settlements.filter(s => s.status === 'CUT OFF').map(s => s.name).join(', ') || '—'} color="#e0115f" />
      </div>}

      <Panel title={`Map · event ${d.event_utc.slice(0, 16)} UTC · blue = floodwater (AI), brown = possible debris (rule, low confidence), amber = objects on debris, red/orange = objects in floodwater, dots = settlements`} className="mt-4">
        <SpaceMap d={d} />
        <p className="mt-2 text-[11px] text-mute">Radar pairs (same orbit): {d.s1_pairs.map(p => `track ${p.orbit} ${p.state} ${p.before_t.slice(0, 10)} → ${p.after_t.slice(0, 16)}`).join(' · ')}. Click a settlement for its route.</p>
      </Panel>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.2fr_1fr]">
        <Panel title="Who is cut off? (road graph before vs after, flooded roads and bridges removed)">
          <div className="max-h-80 overflow-y-auto">
            <table className="w-full text-sm">
              <thead><tr className="text-left font-mono text-xs text-mute"><th className="py-1 font-normal">Settlement</th><th className="font-normal">Status</th><th className="font-normal">Route before</th><th className="font-normal">After</th></tr></thead>
              <tbody>{[...d.cutoff.settlements].sort((a, b) => (a.status === 'CUT OFF' ? -1 : 1) - (b.status === 'CUT OFF' ? -1 : 1)).map((s, i) => (
                <tr key={i} className="border-t border-line"><td className="py-1">{s.name ?? '—'} <span className="text-mute">{s.place}</span></td>
                  <td style={{ color: STATUS_COLOR[s.status] }}>{s.status}</td><td className="font-mono">{s.before_km ?? '—'} km</td><td className="font-mono">{s.after_km == null ? 'no route' : `${s.after_km} km`}</td></tr>))}</tbody>
            </table>
          </div>
        </Panel>
        <Panel title="AI model · U-Net trained on Kuro Siwo, tested on unseen flood events">
          <table className="w-full font-mono text-sm">
            <thead><tr className="text-left text-xs text-mute"><th className="py-1 font-normal">Class</th><th className="font-normal">Precision</th><th className="font-normal">Recall</th><th className="font-normal">F1</th><th className="font-normal">IoU</th></tr></thead>
            <tbody>{([['Flood (tuned threshold)', t?.flood_tuned], ['Flood (arg-max)', t?.flood_argmax], ['Any water', t?.any_water]] as [string, Score | undefined][]).map(([k, v]) => (
              <tr key={k} className="border-t border-line"><td className="py-1 font-sans">{k}</td><td>{f(v?.precision)}</td><td>{f(v?.recall)}</td><td className="text-brand">{f(v?.f1)}</td><td>{f(v?.iou)}</td></tr>))}</tbody>
          </table>
          <p className="mt-2 text-[11px] text-mute">Flood threshold {f(d.model.flood_threshold)} chosen on the validation split, never on test. Kuro Siwo test events are mostly lowland floods; no labelled Himalayan scenes exist to score on.</p>
        </Panel>
      </div>

      <Panel title="Situation report (generated by the system; every number comes from the maps)" className="mt-4">
        <pre className="max-h-96 overflow-y-auto whitespace-pre-wrap font-sans text-sm leading-relaxed text-ink/85">{d.sitrep.replace(/\*\*/g, '')}</pre>
      </Panel>
    </div>
  )
}
