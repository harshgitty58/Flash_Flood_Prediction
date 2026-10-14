import * as maplibregl from 'maplibre-gl'
import type * as GeoJSON from 'geojson'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import { useEffect, useRef } from 'react'
import { fetchTracked, setCursor, TILE_INDEX_URL, tileUrl, type Coverage } from '../lib/data'

type TileMeta = { z: number; x: number; y: number; bbox: [number, number, number, number]; lon: number; lat: number; n: number; max_s: number }
const TILE_MIN_ZOOM = 11

maplibregl.setWorkerUrl(workerUrl)

export type Basemap = 'dark' | 'satellite' | 'terrain'
export type MapPoint = { id: string; lat: number; lon: number; color: string; size: number; label?: string }

type Props = {
  points: MapPoint[]
  selected?: string | null
  onSelect?: (id: string) => void
  landslides?: [number, number][]
  showLandslides?: boolean
  showHillshade?: boolean
  basemap?: Basemap
  terrain3d?: boolean
  buildings?: GeoJSON.FeatureCollection | null
  tiledBuildings?: boolean // load buildings as viewport tiles (quadtree index) instead of one big GeoJSON
  onBuilding?: (props: Record<string, unknown>) => void
  focus?: { lat: number; lon: number; zoom: number } | null
  landmarks?: GeoJSON.FeatureCollection | null
  coverage?: Coverage | null // gauge circles where buildings were scanned; outside them a 'data unavailable' tooltip shows
  showBuildings?: boolean
  showLabels?: boolean
  cinematic?: boolean // landing hero: 3D terrain, slow orbit, no interaction
  className?: string
}

const BASE = 'https://basemaps.cartocdn.com/gl/dark-matter-nolabels-gl-style/style.json'
const DEM = 'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'
const CENTER: [number, number] = [79.15, 30.05]

export default function FloodMap({ points, selected, onSelect, landslides, showLandslides = false, showHillshade = true, basemap = 'dark', terrain3d = false, buildings, tiledBuildings = false, onBuilding, focus, landmarks, coverage, showBuildings = true, showLabels = true, cinematic = false, className = '' }: Props) {
  const el = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map | null>(null)
  const markers = useRef<maplibregl.Marker[]>([])
  const ready = useRef(false)
  const onBuildingRef = useRef(onBuilding)
  onBuildingRef.current = onBuilding
  const queue = useRef<(() => void)[]>([])
  const covRef = useRef(coverage)
  covRef.current = coverage
  const tip = useRef<HTMLDivElement>(null)

  // "Data unavailable" tooltip: at zoom >= 11, outside every reporting gauge's radius there is no prediction and no
  // building scan, so say so (with the nearest reporting gauge, and an offline gauge if one sits close by).
  const gapTip = (e: maplibregl.MapMouseEvent | null) => {
    const t = tip.current, c = covRef.current, m = map.current
    if (!t) return
    const hide = () => { t.style.opacity = '0' }
    if (!e || !c || !m || m.getZoom() < 11) return hide()
    const k = Math.cos((e.lngLat.lat * Math.PI) / 180)
    const km = (p: { lat: number; lon: number }) => Math.hypot((p.lon - e.lngLat.lng) * 111.32 * k, (p.lat - e.lngLat.lat) * 110.54)
    const near = (ps: Coverage['reporting']) => ps.reduce<[Coverage['reporting'][number] | null, number]>((a, p) => (km(p) < a[1] ? [p, km(p)] : a), [null, Infinity])
    if (c.reporting.some(p => km(p) <= (p.r_km ?? c.radius_km))) return hide()
    const [rep, rd] = near(c.reporting.filter(p => (p.src ?? 0) === 0))
    const [off, od] = near(c.offline)
    const [, , nearEl, offEl] = Array.from(t.children) as HTMLElement[]
    nearEl.textContent = rep ? `Nearest reporting gauge: ${rep.station} · ${rd.toFixed(1)} km` : ''
    offEl.textContent = off && od <= c.radius_km ? `Gauge ${off.station} (${od.toFixed(1)} km away) was offline at the replay time.` : ''
    t.style.transform = `translate(${e.point.x + 16}px, ${e.point.y + 16}px)`
    t.style.opacity = '1'
  }

  useEffect(() => {
    const m = new maplibregl.Map({
      container: el.current!, style: BASE, center: CENTER, zoom: cinematic ? 7.4 : 7.2,
      pitch: cinematic ? 58 : 0, bearing: cinematic ? -18 : 0, interactive: !cinematic, attributionControl: { compact: true },
    })
    map.current = m
    if (cinematic) m.setPadding({ left: el.current!.clientWidth * 0.55, top: 0, right: 0, bottom: 0 })
    m.on('load', () => {
      m.addSource('dem', { type: 'raster-dem', tiles: [DEM], tileSize: 256, encoding: 'terrarium', maxzoom: 12 })
      // tint the CARTO dark basemap toward forest night
      for (const l of m.getStyle().layers) {
        if (l.type === 'background') m.setPaintProperty(l.id, 'background-color', '#0c1f16')
        else if (l.type === 'fill' && /water/.test(l.id)) m.setPaintProperty(l.id, 'fill-color', '#0a2230')
        else if (l.type === 'fill' && /landcover|park|wood|forest/.test(l.id)) m.setPaintProperty(l.id, 'fill-color', '#0c1f14')
        else if (l.type === 'line' && /waterway|river/.test(l.id)) m.setPaintProperty(l.id, 'line-color', '#1d4a63')
      }
      const firstLabel = m.getStyle().layers.find(l => l.type === 'symbol')?.id
      m.addSource('sat', { type: 'raster', tileSize: 256, maxzoom: 19, attribution: 'Imagery © Esri, Maxar, Earthstar Geographics',
        tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'] })
      m.addSource('topo', { type: 'raster', tileSize: 256, maxzoom: 17, attribution: '© OpenTopoMap (CC-BY-SA)',
        tiles: ['https://a.tile.opentopomap.org/{z}/{x}/{y}.png', 'https://b.tile.opentopomap.org/{z}/{x}/{y}.png'] })
      m.addLayer({ id: 'sat', type: 'raster', source: 'sat', layout: { visibility: 'none' } }, firstLabel)
      m.addLayer({ id: 'topo', type: 'raster', source: 'topo', layout: { visibility: 'none' }, paint: { 'raster-saturation': -0.25 } }, firstLabel)
      m.addLayer({ id: 'hillshade', type: 'hillshade', source: 'dem', paint: {
        'hillshade-shadow-color': '#000000', 'hillshade-highlight-color': '#41604b', 'hillshade-accent-color': '#0a1a12', 'hillshade-exaggeration': 0.55,
      } })
      if (cinematic) m.setTerrain({ source: 'dem', exaggeration: 1.6 })
      m.addSource('ls', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
      m.addLayer({ id: 'ls', type: 'circle', source: 'ls', layout: { visibility: 'none' }, paint: {
        'circle-radius': 1.6, 'circle-color': '#ff9f1c', 'circle-opacity': 0.45,
      } })
      const COLOR = ['step', ['get', 's'], '#3ddc97', 20, '#f5d547', 40, '#ff9f1c', 60, '#ff4d2e', 80, '#e0115f'] as unknown as maplibregl.ExpressionSpecification
      m.addSource('bld', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
      m.addLayer({ id: 'bld', type: 'fill', source: 'bld', minzoom: 12, paint: { 'fill-color': COLOR, 'fill-opacity': 0 } })
      // outline style = hazard source: solid live gauge · dashed last gauge report · dotted district estimate (muted)
      const W = ['interpolate', ['linear'], ['zoom'], 12, 0.6, 15, 1.6, 18, 2.6] as maplibregl.ExpressionSpecification
      m.addLayer({ id: 'bld-line', type: 'line', source: 'bld', minzoom: 12, filter: ['==', ['coalesce', ['get', 'src'], 0], 0], paint: { 'line-color': COLOR, 'line-width': W } })
      m.addLayer({ id: 'bld-line-stale', type: 'line', source: 'bld', minzoom: 12, filter: ['==', ['get', 'src'], 1], paint: { 'line-color': COLOR, 'line-width': W, 'line-dasharray': [2, 1.4] } })
      m.addLayer({ id: 'bld-line-est', type: 'line', source: 'bld', minzoom: 12, filter: ['==', ['get', 'src'], 2], paint: { 'line-color': COLOR, 'line-width': W, 'line-opacity': 0.7, 'line-dasharray': [0.5, 1.6] } })
      m.addLayer({ id: 'bld-pt', type: 'circle', source: 'bld', minzoom: 9.5, maxzoom: 12, filter: ['>=', ['get', 's'], 40], paint: {
        'circle-radius': 1.8, 'circle-color': COLOR, 'circle-opacity': 0.9 } })
      // open-source place labels (OSM via CARTO for dark, Esri reference overlay for satellite)
      // open-source place labels: Esri World Boundaries & Places reference overlay (no key; white text with halo)
      m.addSource('lbl', { type: 'raster', tileSize: 256, attribution: 'Labels © Esri', tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}'] })
      m.addLayer({ id: 'lbl', type: 'raster', source: 'lbl', layout: { visibility: 'none' } })
      // named OSM landmarks, coloured by the same exposure score
      m.addSource('lm', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
      m.addLayer({ id: 'lm', type: 'circle', source: 'lm', minzoom: 12, filter: ['==', ['get', 'place'], 0], paint: {
        'circle-radius': 5, 'circle-color': COLOR, 'circle-stroke-color': '#06110c', 'circle-stroke-width': 1.5 } })
      // state-wide OSM place names: towns from z8, villages from z11, hamlets from z13
      for (const [rank, minzoom, size] of [[1, 8, 14], [2, 11, 12], [3, 13, 11]] as const)
        m.addLayer({ id: `pl-${rank}`, type: 'symbol', source: 'lm', minzoom, filter: ['all', ['==', ['get', 'place'], 1], ['==', ['get', 'rank'], rank]], layout: {
          'text-field': ['get', 'name'], 'text-font': ['Montserrat Medium'], 'text-size': size, 'text-optional': true, 'text-max-width': 9,
          'symbol-sort-key': rank }, paint: { 'text-color': '#ffffff', 'text-halo-color': '#06110c', 'text-halo-width': 1.6 } })
      m.addLayer({ id: 'lm-txt', type: 'symbol', source: 'lm', minzoom: 12, filter: ['==', ['get', 'place'], 0], layout: {
        'text-field': ['get', 'name'], 'text-font': ['Montserrat Medium'], 'text-optional': true,
        'text-size': ['case', ['==', ['get', 'place'], 1], 13, 11], 'text-offset': ['case', ['==', ['get', 'place'], 1], ['literal', [0, 0]], ['literal', [0, 1.1]]],
        'text-anchor': ['case', ['==', ['get', 'place'], 1], 'center', 'top'], 'text-max-width': 9 }, paint: {
        'text-color': ['case', ['==', ['get', 'place'], 1], '#ffffff', COLOR], 'text-halo-color': '#06110c', 'text-halo-width': 1.6 } })
      ready.current = true
      queue.current.splice(0).forEach(fn => fn())
      if (cinematic) {
        const orbit = () => { m.easeTo({ bearing: m.getBearing() + 12, duration: 20000, easing: (t: number) => t }) }
        m.on('moveend', orbit); orbit()
      }
    })
    if (!cinematic) {
      m.on('mousemove', e => { setCursor({ lat: e.lngLat.lat, lon: e.lngLat.lng }); gapTip(e) })
      m.on('movestart', () => gapTip(null))
      m.getCanvasContainer().addEventListener('mouseleave', () => { setCursor(null); gapTip(null) })
    }
    if (!cinematic) for (const id of ['bld', 'lm']) {
      m.on('click', id, e => { const f = e.features?.[0]; if (f && onBuildingRef.current) onBuildingRef.current({ ...f.properties, _type: id }) })
      m.on('mouseenter', id, () => { m.getCanvas().style.cursor = 'pointer' })
      m.on('mouseleave', id, () => { m.getCanvas().style.cursor = '' })
    }
    if (!cinematic) m.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-left')
    return () => { m.remove(); map.current = null; ready.current = false }
  }, [cinematic])

  // layers that depend on props
  useEffect(() => {
    const m = map.current; if (!m) return
    const apply = () => {
      // re-read the live instance: under StrictMode a queued apply can outlive the map it was created for
      const m = map.current
      if (!m || !m.getLayer('hillshade')) return
      m.setLayoutProperty('hillshade', 'visibility', showHillshade ? 'visible' : 'none')
      m.setLayoutProperty('sat', 'visibility', basemap === 'satellite' ? 'visible' : 'none')
      m.setLayoutProperty('topo', 'visibility', basemap === 'terrain' ? 'visible' : 'none')
      m.setPaintProperty('hillshade', 'hillshade-exaggeration', basemap === 'dark' ? 0.55 : 0.3)
      if (!cinematic) {
        m.setTerrain(terrain3d ? { source: 'dem', exaggeration: 1.5 } : null)
        m.easeTo({ pitch: terrain3d ? 60 : 0, duration: 800 })
      }
      const empty: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] }
      if (!tiledBuildings) (m.getSource('bld') as maplibregl.GeoJSONSource).setData((showBuildings && buildings) || empty)
      for (const id of ['bld', 'bld-line', 'bld-line-stale', 'bld-line-est', 'bld-pt', 'bld-ov']) if (m.getLayer(id)) m.setLayoutProperty(id, 'visibility', showBuildings ? 'visible' : 'none')
      ;(m.getSource('lm') as maplibregl.GeoJSONSource).setData((showLabels && landmarks) || empty)
      m.setLayoutProperty('lbl', 'visibility', showLabels && !cinematic && basemap !== 'terrain' ? 'visible' : 'none')
      m.setLayoutProperty('ls', 'visibility', showLandslides ? 'visible' : 'none')
      if (landslides) (m.getSource('ls') as maplibregl.GeoJSONSource).setData({
        type: 'FeatureCollection',
        features: landslides.map(c => ({ type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates: c } })),
      })
    }
    if (ready.current) apply(); else queue.current.push(apply)
  }, [landslides, showLandslides, showHillshade, basemap, terrain3d, buildings, tiledBuildings, landmarks, showBuildings, showLabels, cinematic])

  useEffect(() => {
    const m = map.current; if (!m) return
    markers.current.forEach(mk => mk.remove())
    markers.current = points.map(p => {
      const d = document.createElement('div')
      d.className = 'hotspot' + (p.id === selected ? ' sel' : '')
      d.style.setProperty('--c', p.color); d.style.setProperty('--s', `${p.size}px`)
      d.innerHTML = '<span class="pulse"></span>'
      if (p.label) d.title = p.label
      if (onSelect) d.onclick = e => { e.stopPropagation(); onSelect(p.id) }
      return new maplibregl.Marker({ element: d }).setLngLat([p.lon, p.lat]).addTo(m)
    })
  }, [points, selected, onSelect])

  useEffect(() => {
    const p = points.find(x => x.id === selected)
    if (p && map.current && !cinematic) map.current.flyTo({ center: [p.lon, p.lat], zoom: Math.max(map.current.getZoom(), 8.6), duration: 1200 })
  }, [selected]) // eslint-disable-line react-hooks/exhaustive-deps

  // Viewport tiling: fetch only the quadtree tiles intersecting the view (zoom >= 11), cache them, and show a
  // one-marker-per-tile overview below that zoom. Replaces one 8.7 MB download with ~100-600 KB per view.
  useEffect(() => {
    const m = map.current
    if (!m || !tiledBuildings || cinematic) return
    const cache = new Map<string, GeoJSON.Feature[]>()
    let index: TileMeta[] = []
    let alive = true
    const key = (t: TileMeta) => `${t.z}/${t.x}/${t.y}`
    const refresh = async () => {
      if (!alive || !index.length || m.getZoom() < TILE_MIN_ZOOM) return
      const b = m.getBounds()
      const vis = index.filter(t => t.bbox[0] <= b.getEast() && t.bbox[2] >= b.getWest() && t.bbox[1] <= b.getNorth() && t.bbox[3] >= b.getSouth())
      await Promise.all(vis.filter(t => !cache.has(key(t))).map(t =>
        fetchTracked<GeoJSON.FeatureCollection>(tileUrl(t.z, t.x, t.y)).then(fc => { cache.set(key(t), fc.features) })))
      if (!alive) return
      const features = vis.flatMap(t => cache.get(key(t)) ?? [])
      ;(m.getSource('bld') as maplibregl.GeoJSONSource).setData({ type: 'FeatureCollection', features })
    }
    const init = () => {
      fetchTracked<{ tiles: TileMeta[] }>(TILE_INDEX_URL).then(({ tiles }) => {
        if (!alive) return
        index = tiles
        const ov: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: tiles.map(t => ({
          type: 'Feature', properties: { n: t.n, s: t.max_s }, geometry: { type: 'Point', coordinates: [t.lon, t.lat] } })) }
        if (!m.getSource('bld-ov')) {
          m.addSource('bld-ov', { type: 'geojson', data: ov })
          m.addLayer({ id: 'bld-ov', type: 'circle', source: 'bld-ov', maxzoom: TILE_MIN_ZOOM, paint: {
            'circle-radius': ['interpolate', ['linear'], ['sqrt', ['get', 'n']], 1, 3, 70, 16],
            'circle-color': ['step', ['get', 's'], '#3ddc97', 20, '#f5d547', 40, '#ff9f1c', 60, '#ff4d2e', 80, '#e0115f'],
            'circle-opacity': 0.35, 'circle-stroke-width': 1, 'circle-stroke-color': '#f1f8f3', 'circle-stroke-opacity': 0.4 } })
        }
        refresh()
      })
      m.on('moveend', refresh)
    }
    if (ready.current) init(); else queue.current.push(init)
    return () => { alive = false; m.off('moveend', refresh) }
  }, [tiledBuildings, cinematic])

  useEffect(() => {
    if (focus && map.current) map.current.flyTo({ center: [focus.lon, focus.lat], zoom: focus.zoom, duration: 2000 })
  }, [focus])

  return (
    <div className={`h-full w-full ${/\b(absolute|fixed)\b/.test(className) ? '' : 'relative'} ${className}`}>
      <div ref={el} className="h-full w-full" />
      <div ref={tip} role="status" aria-live="polite" style={{ opacity: 0, transition: 'opacity 220ms ease' }}
        className="glass-strong pointer-events-none absolute left-0 top-0 z-20 max-w-[270px] rounded-xl px-3 py-2 text-[11px] leading-snug shadow-lg">
        <div className="font-semibold text-ink">Data unavailable</div>
        <div className="text-ink/80">No rain gauge reporting nearby and not near a listed town, so there is no prediction or building scan here.</div>
        <div className="mt-1 font-mono text-[10px] text-mute" />
        <div className="font-mono text-[10px] text-mute" />
      </div>
    </div>
  )
}
