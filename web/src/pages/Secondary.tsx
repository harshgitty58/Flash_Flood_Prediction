import { Area, Bar as RBar, BarChart, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { PageHead, Panel, Pending, Stat } from '../components/ui'
import { fmtTime, pct, useData, type Events as EventsData, type Metrics, type Snapshot, type TimelinePt } from '../lib/data'

const axis = { fontSize: 11, fill: '#a9c2b3' }
const tip = { contentStyle: { background: '#10231a', border: '1px solid #213c30', borderRadius: 8, fontSize: 12 } }

export function Forecast() {
  const tl = useData<TimelinePt[]>('timeline')
  const snap = useData<Snapshot>('snapshot')
  const lead = useData<Metrics>('metrics')?.verification?.lead_time
  if (!tl || !snap) return null
  const T = snap.replay_time.slice(0, 16)
  const after = tl.filter(p => p.t > T)
  const peak = after.reduce<TimelinePt | null>((a, b) => (!a || b.max_p > a.max_p ? b : a), null)
  const data = tl.map(p => ({ ...p, band: [p.q10, p.q90] }))

  return (
    <div className="mx-auto max-w-6xl p-6">
      <PageHead kicker="02 · Time" title="Forecast" question="What is likely to happen over the next few hours?" />
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label="Now (peak station)" value={pct(snap.peak_p)} color="var(--color-severe)" />
        <Stat label="Peak, next 24 h" value={peak ? pct(peak.max_p) : '—'} sub={peak ? fmtTime(peak.t) : 'no predictions after replay time'} />
        <Stat label="Warned before the event day" value={lead ? `${lead.warned_before}/${lead.events}` : '—'}
          sub={lead ? `median lead ${lead.median_lead_h ?? '—'} h (first sustained ≥ ALERT); ${lead.baseline_only} already on as a district baseline, ${lead.missed} missed. Nowcast: no weather-forecast input.` : 'see Metrics'} />
        <Stat label="Stations in window" value={Math.max(...tl.map(p => p.n))} sub="max per hour" />
      </div>
      <Panel title="Flood probability · replay window" className="mt-4">
        <div className="h-80">
          <ResponsiveContainer>
            <ComposedChart data={data} margin={{ right: 10 }}>
              <XAxis dataKey="t" tick={axis} tickFormatter={t => t.slice(5, 13).replace('T', ' ')} minTickGap={40} />
              <YAxis domain={[0, 1]} tick={axis} tickFormatter={v => `${v * 100}%`} />
              <Tooltip {...tip} formatter={(v) => Array.isArray(v) ? v.map(x => pct(Number(x))).join(' – ') : pct(Number(v))} />
              <Area dataKey="band" name="Station spread (p10–p90)" stroke="none" fill="#38bdf8" fillOpacity={0.15} />
              <Line dataKey="mean_p" name="Mean" stroke="#38bdf8" dot={false} strokeWidth={1.5} />
              <Line dataKey="max_p" name="Max station" stroke="#ff4d2e" dot={false} strokeWidth={2.5} />
              <ReferenceLine x={T} stroke="#f1f8f3" strokeDasharray="4 4" label={{ value: 'REPLAY T', fill: '#f1f8f3', fontSize: 10, position: 'top' }} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-2 text-[11px] text-mute">Probabilities are Venn-Abers calibrated. Shaded band = spread across reporting stations (p10–p90); per-station confidence is in the Risk Map drawer.</p>
      </Panel>
    </div>
  )
}

export function Events() {
  const ev = useData<EventsData>('events')
  if (!ev) return null
  const byYear = Object.entries(ev.floods.reduce<Record<string, number>>((a, f) => { const y = f.start.slice(0, 4); a[y] = (a[y] ?? 0) + 1; return a }, {}))
    .map(([year, n]) => ({ year, n })).sort((a, b) => a.year.localeCompare(b.year))
  const recent = [...ev.floods].sort((a, b) => b.start.localeCompare(a.start)).slice(0, 14)

  return (
    <div className="mx-auto max-w-6xl p-6">
      <PageHead kicker="06 · Validation" title="Events" question="How did the model perform on historical flood events?" />
      <Panel title={`Recorded flood events · IMD inventory (${ev.floods.length})`}>
        <div className="h-48">
          <ResponsiveContainer>
            <BarChart data={byYear}><XAxis dataKey="year" tick={axis} minTickGap={16} /><YAxis tick={axis} allowDecimals={false} width={24} /><Tooltip {...tip} cursor={{ fill: '#ffffff08' }} /><RBar dataKey="n" name="Events" fill="#ff4d2e" radius={[3, 3, 0, 0]} /></BarChart>
          </ResponsiveContainer>
        </div>
      </Panel>
      <div className="mt-4 grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Panel title="Most recent events">
          <table className="w-full text-sm">
            <tbody>{recent.map(f => (
              <tr key={f.UEI} className="border-t border-line first:border-0">
                <td className="py-2 font-mono text-xs text-mute">{f.start}</td><td className="py-2">{f.districts}</td>
                <td className="py-2 text-mute">{f.cause}</td><td className="py-2 text-right font-mono">{f.fatalities ?? '—'}</td>
              </tr>))}</tbody>
          </table>
          <p className="mt-2 text-[11px] text-mute">Last column: reported fatalities.</p>
        </Panel>
        <Pending title="Event replay with predicted vs observed">Timeline playback (T−6 h → event) and hit / miss / false-alarm counts per event. Built after event-level evaluation; no lead-time numbers are shown until they are measured.</Pending>
      </div>
    </div>
  )
}
