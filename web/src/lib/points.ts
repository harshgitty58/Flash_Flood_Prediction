import { useMemo } from 'react'
import type { MapPoint } from '../components/FloodMap'
import { pretty, TIER_COLOR, type Snapshot, type Station } from './data'

/** Stations with a replay prediction get a tier-coloured hotspot sized by probability; others render as dim "no data". */
export function useRiskPoints(stations: Station[] | null, snap: Snapshot | null, includeIdle = true): MapPoint[] {
  return useMemo(() => {
    if (!stations || !snap) return []
    const byId = new Map(snap.stations.map(s => [s.station, s]))
    return stations.filter(s => s.kind === 'rain').flatMap(s => {
      const r = byId.get(s.station)
      if (!r) return includeIdle ? [{ id: s.station, lat: s.lat, lon: s.lon, color: '#4b5563', size: 12, label: `${pretty(s.station)} — no data` }] : []
      return [{ id: s.station, lat: s.lat, lon: s.lon, color: TIER_COLOR[r.tier], size: 16 + r.p * 34, label: `${pretty(s.station)} — ${(r.p * 100).toFixed(0)}%` }]
    })
  }, [stations, snap, includeIdle])
}
