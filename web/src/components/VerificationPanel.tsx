import { useState } from 'react'
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from 'recharts'
import type { Metrics } from '../lib/data'
import { Panel } from './ui'

const axis = { fontSize: 11, fill: '#a9c2b3' }
const tip = { contentStyle: { background: '#10231a', border: '1px solid #213c30', fontSize: 12 } }
const f = (v: number | null | undefined, d = 2) => (v == null ? '—' : v.toFixed(d))

function Seg<T extends string>({ value, options, onChange }: { value: T; options: [T, string][]; onChange: (v: T) => void }) {
  return (
    <div className="flex gap-1 rounded-full border border-white/10 bg-white/[.04] p-1 font-mono text-[11px]">
      {options.map(([v, l]) => (
        <button key={v} onClick={() => onChange(v)} className={`rounded-full px-3 py-1 transition ${value === v ? 'bg-ink text-bg' : 'text-ink/70 hover:text-ink'}`}>{l}</button>
      ))}
    </div>
  )
}

/** WMO-style verification: contingency scores with bootstrap CIs, BSS + reliability, honest lead time, economic value. */
export default function VerificationPanel({ v }: { v: NonNullable<Metrics['verification']> }) {
  const [unit, setUnit] = useState<'district-day' | 'station-hour'>('district-day')
  const [split, setSplit] = useState<'test' | 'validation' | 'both'>('both')
  const [level, setLevel] = useState<'≥ ALERT' | '≥ SEVERE'>('≥ ALERT')
  const rows = v.contingency.filter(r => r.unit === unit && r.split === split && r.level === level)
  const best = Math.max(...rows.map(r => r.CSI ?? 0))
  const p = v.probabilistic['station-hour']
  const lt = v.lead_time
  const when = (h: number | null) => (h == null ? '—' : h >= 0 ? `${h} h before the event day` : `${-h} h into the event day`)

  return (
    <>
      <Panel title="Industry-standard verification · contingency scores (WMO-style)" className="mt-4">
        <div className="mb-3 flex flex-wrap gap-2">
          <Seg value={unit} onChange={setUnit} options={[['district-day', 'District-day'], ['station-hour', 'Station-hour']]} />
          <Seg value={split} onChange={setSplit} options={[['both', 'Jul + Aug 2023'], ['validation', 'Validation'], ['test', 'Test']]} />
          <Seg value={level} onChange={setLevel} options={[['≥ ALERT', '≥ ALERT'], ['≥ SEVERE', '≥ SEVERE']]} />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full font-mono text-sm">
            <thead>
              <tr className="text-left text-xs text-mute">
                {['Layer / baseline', 'Hits', 'Misses', 'False alarms', 'POD', 'FAR', 'CSI (95 % CI)', 'ETS', 'HSS', 'Bias'].map(h => <th key={h} className="py-2 pr-3 font-normal">{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.layer} className={`border-t border-line ${r.layer.includes('deployed') ? 'text-brand' : ''}`}>
                  <td className="py-1.5 pr-3 font-sans">{r.layer}{r.CSI === best && best > 0 ? ' ★' : ''}</td>
                  <td>{r.tp}</td><td>{r.fn}</td><td>{r.fp.toLocaleString()}</td>
                  <td>{f(r.POD)}</td><td>{f(r.FAR)}</td>
                  <td>{f(r.CSI, 3)} <span className="text-[10px] text-mute">[{r.ci95.CSI?.map(x => x.toFixed(2)).join(', ')}]</span></td>
                  <td>{f(r.ETS, 3)}</td><td>{f(r.HSS, 3)}</td><td>{f(r.bias, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-[11px] text-mute">
          {rows[0] ? `${rows[0].events} flood ${unit === 'district-day' ? 'district-days' : 'hours'} in ${rows[0].n.toLocaleString()} ${unit}s (base rate ${(rows[0].base_rate * 100).toFixed(1)} %). ` : ''}
          POD = share of floods warned · FAR = share of warnings that were false · CSI = hits / (hits + misses + false alarms) · ETS / HSS = skill over chance (0 = none) · bias &gt; 1 = over-warning.
          CIs: block bootstrap over days (1,000 resamples). ★ = best CSI. Wide intervals mean too few flood events to separate the layers.
        </p>
      </Panel>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Panel title={`Probabilistic skill · station-hour · BSS ${f(p.BSS, 3)} · ECE ${f(v.probabilistic.ECE_station_hour, 3)}`}>
          <div className="h-56">
            <ResponsiveContainer>
              <ScatterChart margin={{ right: 12, bottom: 4 }}>
                <CartesianGrid stroke="#213c30" />
                <XAxis type="number" dataKey="mean_pred" name="predicted" tick={axis} domain={[0, 'auto']} tickFormatter={x => `${(x * 100).toFixed(0)}%`} />
                <YAxis type="number" dataKey="obs_freq" name="observed" tick={axis} domain={[0, 'auto']} tickFormatter={x => `${(x * 100).toFixed(0)}%`} />
                <ZAxis dataKey="n" range={[40, 260]} />
                <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 0.3, y: 0.3 }]} stroke="#a9c2b3" strokeDasharray="4 4" />
                <Tooltip {...tip} formatter={x => `${(Number(x) * 100).toFixed(2)}%`} />
                <Scatter data={v.probabilistic.reliability_station_hour} fill="#a3e635" line={{ stroke: '#a3e635' }} />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-2 text-[11px] text-mute">
            Reliability diagram: points on the dashed diagonal = well calibrated. Brier {f(p.brier, 4)} vs climatology {f(p.brier_climatology, 4)} (training base rate per month)
            → Brier Skill Score {f(p.BSS, 3)}: a small real improvement over always forecasting the base rate.
          </p>
        </Panel>

        <Panel title={`Honest lead time · ${lt.warned_before}/${lt.events} warned · ${lt.baseline_only} baseline-only · ${lt.missed} missed`}>
          <table className="w-full text-sm">
            <thead><tr className="text-left font-mono text-xs text-mute"><th className="py-1 font-normal">Event day</th><th className="font-normal">District</th><th className="font-normal">Status</th><th className="font-normal">Switch-on</th></tr></thead>
            <tbody>
              {lt.events_table.map((e, i) => (
                <tr key={i} className="border-t border-line">
                  <td className="py-1 font-mono text-xs">{e.event_day}</td><td>{e.district}</td>
                  <td className={e.status === 'warned' ? 'text-brand' : e.status === 'missed' ? 'text-severe' : 'text-mute'}>{e.status}</td>
                  <td className="font-mono text-xs">{when(e.lead_h_before_event_day)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-[11px] text-mute">
            First ≥ ALERT that persists ≥ 3 h in the 48 h before the event day; gauges already at ALERT most of the 24 h before that window count as "baseline", not warnings.
            Median switch-on: {when(lt.median_lead_h)}. Flood times within a day are unknown (IMD gives dates only).
          </p>
        </Panel>
      </div>

      <Panel title="Relative economic value · deployed hybrid, district-day, ≥ ALERT" className="mt-4">
        <div className="h-48">
          <ResponsiveContainer>
            <LineChart data={v.relative_value} margin={{ right: 12 }}>
              <CartesianGrid stroke="#213c30" />
              <XAxis dataKey="alpha" tick={axis} tickFormatter={x => Number(x).toFixed(1)} />
              <YAxis tick={axis} domain={[-1, 1]} allowDataOverflow />
              <ReferenceLine y={0} stroke="#a9c2b3" strokeDasharray="4 4" />
              <Tooltip {...tip} formatter={x => Number(x).toFixed(3)} labelFormatter={x => `cost/loss ${x}`} />
              <Line dataKey="value" stroke="#4fb3f0" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-2 text-[11px] text-mute">
          Value &gt; 0 = acting on the warning beats both "always act" and "never act" for a user whose protective action costs that fraction of the potential loss (Richardson 2000).
        </p>
      </Panel>
    </>
  )
}
