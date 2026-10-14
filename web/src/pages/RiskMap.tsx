import { useState } from 'react'
import type { Basemap } from '../components/FloodMap'
import FloodMap from '../components/FloodMap'
import ObjectCard, { type ObjProps } from '../components/ObjectCard'
import StationDrawer from '../components/StationDrawer'
import { BasemapSwitch } from '../components/ui'
import type * as GeoJSON from 'geojson'
import { pct, pretty, TIER_COLOR, useData, type Events, type Impact, type Snapshot, type Station } from '../lib/data'
import { useRiskPoints } from '../lib/points'

const LAYERS = [
  ['risk', 'Flood probability', true],
  ['hillshade', 'Terrain hillshade', true],
  ['landslides', 'Landslide inventory', true],
  ['extent', 'Flood extent', false],
  ['depth', 'Water depth', false],
  ['buildings', 'Buildings (impact outlines)', true],
  ['labels', 'Place names & landmarks', true],
] as const

export default function RiskMap() {
  const stations = useData<Station[]>('stations')
  const snap = useData<Snapshot>('snapshot')
  const events = useData<Events>('events')
  const [on, setOn] = useState<Record<string, boolean>>({ risk: true, hillshade: true, landslides: false, buildings: true, labels: true })
  const [sel, setSel] = useState<string | null>(null)
  const [base, setBase] = useState<Basemap>('dark')
  const [is3d, set3d] = useState(false)
  const points = useRiskPoints(stations, snap)
  const marks = useData<GeoJSON.FeatureCollection>('landmarks')
  const im = useData<Impact>('impact')
  const [obj, setObj] = useState<ObjProps | null>(null)
  const selSnap = snap?.stations.find(s => s.station === sel)

  return (
    <div className="relative h-full min-h-[600px]">
      <FloodMap basemap={base} terrain3d={is3d} points={on.risk ? points : []} selected={sel} onSelect={setSel}
        landslides={events?.landslide_points} showLandslides={on.landslides} showHillshade={on.hillshade}
        tiledBuildings landmarks={marks} coverage={im?.coverage} showBuildings={on.buildings} showLabels={on.labels} onBuilding={p => { setSel(null); setObj(p as unknown as ObjProps) }} />

      <div className="glass absolute left-4 top-4 w-60 rounded-xl p-4">
        <div className="label mb-3">Layers</div>
        {LAYERS.map(([k, label, ready]) => (
          <label key={k} className={`flex items-center justify-between py-1 text-sm ${ready ? 'cursor-pointer' : 'opacity-40'}`}>
            <span>{label}{!ready && <span className="ml-1 font-mono text-[9px] uppercase">soon</span>}</span>
            <input type="checkbox" disabled={!ready} checked={!!on[k]} onChange={e => setOn({ ...on, [k]: e.target.checked })} className="accent-[var(--color-brand)]" />
          </label>
        ))}
      </div>

      {snap && (
        <div className="glass absolute bottom-4 left-4 max-h-[45%] w-60 overflow-y-auto rounded-xl p-4">
          <div className="label mb-2">Ranked stations</div>
          {snap.stations.slice(0, 12).map((s, i) => (
            <button key={s.station} onClick={() => { setObj(null); setSel(s.station) }}
              className={`flex w-full items-center gap-2 rounded px-1.5 py-1 text-left text-sm hover:bg-panel ${sel === s.station ? 'bg-panel' : ''}`}>
              <span className="w-4 font-mono text-[10px] text-mute">{i + 1}</span>
              <span className="h-2 w-2 rounded-full" style={{ background: TIER_COLOR[s.tier] }} />
              <span className="flex-1 truncate">{pretty(s.station)}</span>
              <span className="font-mono text-xs">{s.trigger === 'rainfall' ? `${(s.signals.rain_24h ?? 0).toFixed(0)} mm` : pct(s.p)}</span>
            </button>
          ))}
        </div>
      )}
      <div className="absolute left-1/2 top-4 -translate-x-1/2"><BasemapSwitch value={base} onChange={setBase} is3d={is3d} on3d={set3d} /></div>
      {selSnap && !obj && <StationDrawer s={selSnap} onClose={() => setSel(null)} />}
      {obj && im && <ObjectCard o={obj} stations={im.station_p} onClose={() => setObj(null)} />}
    </div>
  )
}
