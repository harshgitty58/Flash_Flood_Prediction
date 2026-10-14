import { pct, pretty } from '../lib/data'

export const IMPACT_CLASSES: [number, string, string][] = [[80, 'CRITICAL', '#e0115f'], [60, 'HIGH', '#ff4d2e'], [40, 'MODERATE', '#ff9f1c'], [20, 'LOW', '#f5d547'], [0, 'MINIMAL', '#3ddc97']]
export const impactClass = (s: number) => IMPACT_CLASSES.find(([cut]) => s >= cut)!

export type ObjProps = { _type: 'bld' | 'lm'; s: number; st: number; h: number; d: number; z?: number; i?: number; a?: number; name?: string; kind?: string }

export default function ObjectCard({ o, stations, onClose }: { o: ObjProps; stations: { station: string; p: number; src?: number; tier?: string; last?: string | null; rank?: number | null }[]; onClose: () => void }) {
  const [, cls, color] = impactClass(o.s)
  const st = stations[o.st]
  const title = o._type === 'bld' ? `B${String(o.i).padStart(5, '0')}` : o.name
  const rows: [string, string][] = [
    ['Hazard source', !st ? '—' : st.src === 2 ? `District estimate · ${st.station.replace(' (district estimate)', '')} · district rank ${st.rank} today (not a gauge reading)`
      : st.src === 1 ? `Last report of ${pretty(st.station)} · ${st.last} · ${st.tier}` : `${pretty(st.station)} · ${st.tier ?? ''} · ${pct(st.p)}`],
    ['River-setback zone', o.z == null ? '—' : ['A · ≤ 50 m (NGT: no construction)', 'B · 50–100 m (NGT regulatory / Jal Shakti interim no-development)', 'C · 100–200 m (Uttarakhand HC: no construction)', 'outside official zones'][o.z]],
    ['Distance to river / stream', `${o.d} m`],
    ['Height above nearest river (info only)', `${o.h} m`],
    ...(o.a ? [['Footprint area', `${o.a} m²`] as [string, string]] : []),
    ['Water depth', 'pending (inundation model)'],
  ]
  return (
    <aside className="glass rise absolute right-4 top-4 z-10 w-[310px] max-w-[calc(100%-2rem)] rounded-2xl p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="label">{o._type === 'bld' ? 'Building · ML-detected footprint' : `Landmark · ${(o.kind ?? '').replace(/_/g, ' ')}`}</div>
          <h2 className="mt-1 truncate text-xl font-semibold">{title}</h2>
        </div>
        <button onClick={onClose} className="text-mute hover:text-ink" aria-label="Close">✕</button>
      </div>
      <div className="mt-4 flex items-end justify-between">
        <div className="font-display text-5xl uppercase leading-none" style={{ color }}>{cls}</div>
        <div className="font-mono text-sm text-mute">{o.s}/100</div>
      </div>
      <div className="mt-1 text-xs text-mute">Possible impact (exposure score)</div>
      <dl className="mt-4 space-y-2 text-sm">
        {rows.map(([k, v]) => <div key={k} className="flex justify-between gap-3 border-b border-line pb-2"><dt className="text-mute">{k}</dt><dd className="text-right font-mono">{v}</dd></div>)}
      </dl>
      <p className="mt-3 text-[11px] text-mute">Class = hazard tier (IMD rainfall categories / hybrid model) stepped down by official river-setback zone: A ≤ 50 m (NGT 2017) keeps the tier, B 50–100 m (NGT / Jal Shakti 2025) one level lower, C 100–200 m (Uttarakhand HC 2013) two lower. Exposure class, not a damage estimate.</p>
    </aside>
  )
}
