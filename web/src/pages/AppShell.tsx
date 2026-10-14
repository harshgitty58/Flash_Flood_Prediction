import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import type * as GeoJSON from 'geojson'
import { useMemo } from 'react'
import { fmtTime, pretty, useCursor, useData, type Snapshot, type Station } from '../lib/data'

// grouped navigation: [group label, items]
const GROUPS: [string, string[]][] = [
  ['Situation', ['overview', 'forecast', 'map', 'impact']],
  ['Analysis', ['uncertainty', 'events']],
  ['Validation', ['model', 'metrics']],
  ['Space · Track B', ['space']],
  ['Platform', ['system']],
]
const NAV = [
  ['space', 'Space mode', 'M12 2l2.5 5 5.5.8-4 3.9.9 5.5L12 14.6 7.1 17.2l.9-5.5-4-3.9 5.5-.8z'],
  ['overview', 'Overview', 'M3 12l9-8 9 8M5 10v10h14V10'],
  ['forecast', 'Forecast', 'M3 17l5-6 4 3 8-9M14 5h6v6'],
  ['map', 'Risk Map', 'M9 4l-6 2v14l6-2 6 2 6-2V4l-6 2-6-2zM9 4v14M15 6v14'],
  ['impact', 'Impact', 'M3 21V9l6-4 6 4v12M15 21V12h6v9M7 13h4M7 17h4'],
  ['uncertainty', 'Uncertainty', 'M12 3a9 9 0 100 18 9 9 0 000-18zM9.5 9a2.5 2.5 0 114 2c-1 .7-1.5 1.2-1.5 2.5M12 17h.01'],
  ['events', 'Events', 'M4 5h16v15H4zM4 10h16M9 3v4M15 3v4'],
  ['model', 'Data & Model', 'M4 6h16M4 12h10M4 18h6M18 14l3 3-3 3'],
  ['metrics', 'Metrics', 'M4 20V10M10 20V4M16 20v-7M22 20H2'],
  ['system', 'System', 'M12 2v4M12 18v4M4.9 4.9l2.8 2.8M16.3 16.3l2.8 2.8M2 12h4M18 12h4M4.9 19.1l2.8-2.8M16.3 7.7l2.8-2.8'],
]

export default function AppShell() {
  const { pathname } = useLocation()
  const snap = useData<Snapshot>('snapshot')
  const cur = useCursor()
  const stations = useData<Station[]>('stations')
  const marks = useData<GeoJSON.FeatureCollection>('landmarks')
  const places = useMemo(() => [
    ...(marks?.features ?? []).filter(f => f.properties?.place).map(f => {
      const [lon, lat] = (f.geometry as GeoJSON.Point).coordinates
      return { name: String(f.properties?.name), lat, lon, district: '' }
    }),
    ...(stations ?? []).map(s => ({ name: pretty(s.station), lat: s.lat, lon: s.lon, district: s.district })),
  ], [marks, stations])
  const near = useMemo(() => {
    if (!cur || !places.length) return null
    const km = (a: { lat: number; lon: number }) => Math.hypot((a.lat - cur.lat) * 110.5, (a.lon - cur.lon) * 111.3 * Math.cos(cur.lat * Math.PI / 180))
    const best = places.reduce((a, b) => (km(b) < km(a) ? b : a))
    const nearestStation = (stations ?? []).reduce<Station | null>((a, b) => (!a || km(b) < km(a) ? b : a), null)
    return { ...best, d: km(best), district: best.district || nearestStation?.district || '' }
  }, [cur, places, stations])
  const byKey = Object.fromEntries(NAV.map(n => [n[0], n]))
  const live = snap?.sources.filter(x => x.status === 'available').length
  return (
    <div className="app-bg flex h-full">
      <aside className="glass-strong z-20 m-2 mr-0 flex w-16 shrink-0 flex-col items-center rounded-2xl py-4 md:w-60 md:items-stretch md:px-3">
        <Link to="/" className="mb-4 flex items-center gap-3 rounded-xl px-2 py-1.5 transition hover:bg-white/5">
          <img src="/prahar-mark.png" alt="PRAHAR" className="h-10 w-auto shrink-0 drop-shadow-[0_0_10px_rgba(79,179,240,.35)]" />
          <span className="hidden md:inline">
            <span className="block font-display text-2xl leading-none tracking-wider text-white">PRAHAR</span>
            <span className="mt-0.5 block whitespace-nowrap font-mono text-[8px] tracking-[.18em] text-brand/80">PREDICT · PREPARE · PROTECT</span>
          </span>
        </Link>
        <nav className="flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto pr-1">
          {GROUPS.map(([g, keys]) => (
            <div key={g}>
              <div className="nav-group hidden md:block">{g}</div>
              {keys.map(k => { const [to, label, d] = byKey[k]; return (
                <NavLink key={to} to={to} title={label} className={({ isActive }) => `nav-item mb-0.5 ${isActive ? 'active' : ''}`}>
                  <svg viewBox="0 0 24 24" className="h-[18px] w-[18px] shrink-0" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d={d} /></svg>
                  <span className="hidden md:inline">{label}</span>
                </NavLink>
              ) })}
            </div>
          ))}
        </nav>
        <div className="mt-3 hidden shrink-0 rounded-xl border border-white/10 bg-white/[.04] p-3 md:block [@media(max-height:820px)]:md:hidden">
          <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-mute"><span className="h-1.5 w-1.5 rounded-full bg-normal shadow-[0_0_8px_var(--color-normal)]" />Model</div>
          <div className="mt-1 text-[11px] leading-snug text-ink/85">{snap?.model}</div>
          {snap && <div className="mt-1.5 font-mono text-[10px] text-mute">sources {live}/{snap.sources.length} · {snap.stations_reporting}/{snap.stations_total} gauges</div>}
        </div>
      </aside>

      <div className="relative flex min-w-0 flex-1 flex-col">
        <header className="glass-strong m-2 mb-0 flex h-14 shrink-0 items-center justify-between rounded-2xl px-5">
          <div className="hidden min-w-0 items-center gap-2 sm:flex">
            <span className="hidden truncate font-mono text-[11px] uppercase tracking-[.18em] text-ink/90 xl:inline">Uttarakhand flash-flood intelligence</span>
            <span className="hidden text-mute xl:inline">/</span>
            <span className="font-mono text-[11px] uppercase tracking-[.18em] text-brand">{(NAV.find(n => pathname.endsWith(n[0])) ?? NAV[0])[1]}</span>
          </div>
          {snap && (
            <div className="ml-4 flex min-w-0 shrink-0 items-center gap-4 font-mono text-xs">
              <span className="flex items-center gap-2 rounded-full border border-alert/40 bg-alert/10 px-3 py-1 text-alert">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-alert" />REPLAY
              </span>
              <span className="whitespace-nowrap text-ink/85">{fmtTime(snap.replay_time)} IST</span>
              {cur && (
                <span className="hidden min-w-0 max-w-[18rem] items-center gap-2 text-mute lg:flex">
                  <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 text-brand" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 21s-7-6.2-7-11.5A7 7 0 0119 9.5C19 14.8 12 21 12 21z" /><circle cx="12" cy="9.5" r="2.5" /></svg>
                  {near && <span className="truncate text-ink">{near.d < 1 ? '' : `${near.d.toFixed(1)} km from `}{near.name}{near.district && `, ${near.district}`}</span>}
                  <span>{Math.abs(cur.lat).toFixed(4)}°{cur.lat >= 0 ? 'N' : 'S'} {Math.abs(cur.lon).toFixed(4)}°{cur.lon >= 0 ? 'E' : 'W'}</span>
                </span>
              )}
            </div>
          )}
        </header>
        <main className="min-h-0 flex-1 overflow-y-auto"><div key={pathname} className="page-in h-full"><Outlet /></div></main>
      </div>
    </div>
  )
}
