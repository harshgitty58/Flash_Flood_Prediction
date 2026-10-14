import { useMemo, useState } from 'react'
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { PageHead, Panel, Stat } from '../components/ui'
import LabelsPanel from '../components/LabelsPanel'
import VerificationPanel from '../components/VerificationPanel'
import { pct, useData, type Metrics as M, type Pod } from '../lib/data'

const NAME: Record<string, string> = { logistic_regression: 'Logistic Regression', random_forest: 'Random Forest', xgboost: 'XGBoost' }
const COLS: [string, string, (v: number) => string][] = [
  ['precision', 'Precision', v => v.toFixed(3)], ['recall', 'Recall', v => v.toFixed(3)], ['f1', 'F1', v => v.toFixed(3)],
  ['specificity', 'Specificity', v => v.toFixed(3)], ['mcc', 'MCC', v => v.toFixed(3)], ['roc_auc', 'ROC-AUC', v => v.toFixed(3)],
  ['pr_auc', 'PR-AUC', v => v.toFixed(3)], ['brier', 'Brier', v => v.toFixed(4)], ['false_alarms_per_station_month', 'False alarms / stn·month', v => v.toFixed(1)],
]
const axis = { fontSize: 11, fill: '#a9c2b3' }

export default function Metrics() {
  const m = useData<M>('metrics')
  const [i, setI] = useState<number | null>(null)
  const curve = m?.pr_curve ?? []
  const best = useMemo(() => curve.reduce((a, b, k) => ((b.f1 ?? 0) > (curve[a]?.f1 ?? 0) ? k : a), 0), [curve])
  if (!m) return null
  const k = i ?? best
  const pt = curve[k]
  const xgbTest = m.hour_level.find(r => r.model === 'xgboost' && r.split === 'test')!
  const cm = m.confusion['xgboost_test']
  const ev = m.event_detection
  const xv = m.external_validation?.summary
  const podText = (p?: Pod) => (p && p.POD != null ? `${p.detected}/${p.n} · ${pct(p.POD)} [${pct(p.ci95[0])}–${pct(p.ci95[1])}]` : '—')
  // A first alert at the very start of the 48 h search window means the alarm was already on (district baseline),
  // not that the model warned 48 h ahead, so it is shown as "already on" rather than as a lead time.
  const leadText = (h: number | null) => h == null ? '—' : h >= 47 ? 'already on' : h <= 0 ? 'same day' : `switched on ${h} h before`

  return (
    <div className="mx-auto max-w-6xl p-6">
      <PageHead kicker="08 · Accuracy" title="Metrics" question="How often is the model right, and what does it miss?" />

      <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
        <Stat label="Precision (test)" value={xgbTest.precision.toFixed(2)} sub="alerts that were real floods" />
        <Stat label="Recall (test)" value={xgbTest.recall.toFixed(2)} sub="flood hours caught" />
        <Stat label="F1 (test)" value={xgbTest.f1.toFixed(2)} sub={`threshold ${xgbTest.threshold}`} />
        <Stat label="Floods detected" value={`${ev.events_detected}/${ev.events_evaluated}`} sub="held-out events" color="var(--color-brand)" />
        <Stat label="External validation" value={xv ? `${xv.hybrid_alert_detected}/${xv.events_with_station_data}` : '—'} sub="documented events after Aug 2023 at ≥ ALERT (hybrid)" />
      </div>

      {m.labels && <LabelsPanel l={m.labels} />}

      {m.verification && <VerificationPanel v={m.verification} />}

      <Panel title="Hour-level metrics at the frozen threshold · validation (Jul 2023) and test (Aug 2023)" className="mt-4">
        <div className="overflow-x-auto">
          <table className="w-full font-mono text-sm">
            <thead><tr className="text-left text-mute"><th className="py-2 font-normal">Model</th><th className="font-normal">Split</th>
              {COLS.map(([, h]) => <th key={h} className="px-2 text-right font-normal">{h}</th>)}</tr></thead>
            <tbody>{m.hour_level.map(r => (
              <tr key={r.model + r.split} className={`border-t border-line ${r.model === 'xgboost' ? 'text-brand' : ''}`}>
                <td className="py-1.5 font-sans">{NAME[r.model]}</td><td className="text-mute">{r.split}</td>
                {COLS.map(([c, , f]) => <td key={c} className="px-2 text-right">{r[c] == null ? '—' : f(Number(r[c]))}</td>)}
              </tr>))}</tbody>
          </table>
        </div>
        <p className="mt-2 text-[11px] text-mute">Rare events: base rate ≈ {pct(m.splits.test.positives / m.splits.test.rows, 1)} of test hours are flood hours, so PR-AUC and F1 matter more than accuracy. Green = deployed model.</p>
      </Panel>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.5fr_1fr]">
        <Panel title="Precision · recall · F1 vs alert threshold (calibrated probability, test)">
          <div className="h-60">
            <ResponsiveContainer>
              <LineChart data={curve} margin={{ right: 8 }}>
                <CartesianGrid stroke="#213c30" />
                <XAxis dataKey="threshold" tick={axis} tickFormatter={v => Number(v).toFixed(2)} />
                <YAxis domain={[0, 1]} tick={axis} />
                <Tooltip contentStyle={{ background: '#10231a', border: '1px solid #213c30', fontSize: 12 }} formatter={v => Number(v).toFixed(3)} labelFormatter={v => `threshold ${Number(v).toFixed(3)}`} />
                <Line dataKey="precision" stroke="#4fb3f0" dot={false} strokeWidth={2} />
                <Line dataKey="recall" stroke="#ff9f1c" dot={false} strokeWidth={2} />
                <Line dataKey="f1" stroke="#a3e635" dot={false} strokeWidth={2.5} />
                {pt && <ReferenceLine x={pt.threshold} stroke="#f1f8f3" strokeDasharray="4 4" />}
              </LineChart>
            </ResponsiveContainer>
          </div>
          <input type="range" min={0} max={curve.length - 1} value={k} onChange={e => setI(+e.target.value)} className="mt-3 w-full accent-[var(--color-brand)]" />
          {pt && <div className="mt-2 grid grid-cols-4 gap-2 font-mono text-sm">
            <div><div className="label">Threshold</div>{pt.threshold.toFixed(3)}</div>
            <div><div className="label">Precision</div><span className="text-water">{pt.precision.toFixed(3)}</span></div>
            <div><div className="label">Recall</div><span className="text-alert">{pt.recall.toFixed(3)}</span></div>
            <div><div className="label">F1</div><span className="text-brand">{(pt.f1 ?? 0).toFixed(3)}</span></div>
          </div>}
          <p className="mt-2 text-[11px] text-mute">Drag to see the trade-off: a lower threshold catches more floods (recall) but raises false alarms (lower precision). Starts at the F1-optimal point.</p>
        </Panel>

        <Panel title="Confusion matrix · XGBoost, test">
          {cm && <div className="grid grid-cols-[auto_1fr_1fr] gap-1 font-mono text-sm">
            <div /><div className="label text-center">pred: no flood</div><div className="label text-center">pred: flood</div>
            <div className="label self-center">actual: no flood</div>
            <div className="rounded bg-normal/15 p-4 text-center text-lg">{cm[0][0].toLocaleString()}<div className="text-[10px] text-mute">TN</div></div>
            <div className="rounded bg-alert/15 p-4 text-center text-lg">{cm[0][1].toLocaleString()}<div className="text-[10px] text-mute">FP · false alarm</div></div>
            <div className="label self-center">actual: flood</div>
            <div className="rounded bg-severe/15 p-4 text-center text-lg">{cm[1][0].toLocaleString()}<div className="text-[10px] text-mute">FN · missed</div></div>
            <div className="rounded bg-brand/15 p-4 text-center text-lg">{cm[1][1].toLocaleString()}<div className="text-[10px] text-mute">TP · caught</div></div>
          </div>}
        </Panel>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Panel title="≥ ALERT as a warning · which layer does the work">
          <table className="w-full font-mono text-sm">
            <thead><tr className="text-left text-mute"><th className="py-1 font-normal">Layer</th><th className="font-normal">Precision</th><th className="font-normal">Recall</th><th className="font-normal">F1</th><th className="font-normal">False-alarm rate</th></tr></thead>
            <tbody>{Object.entries(m.warning_levels).filter(([k2]) => k2.startsWith('test')).map(([k2, v]) => (
              <tr key={k2} className="border-t border-line"><td className="py-1 font-sans">{({ test_tier_ml: 'ML only', test_tier_rain: 'Rainfall (IMD) only', test_tier: 'Hybrid (deployed)' } as Record<string, string>)[k2] ?? k2}</td>
                <td>{v.precision.toFixed(3)}</td><td>{v.recall.toFixed(3)}</td><td>{v.f1.toFixed(3)}</td><td>{pct(v.false_alarm_rate, 1)}</td></tr>))}</tbody>
          </table>
        </Panel>
        <Panel title="Event level · each held-out flood (leave-one-event-out)">
          <div className="max-h-64 overflow-y-auto">
            <table className="w-full text-sm">
              <thead><tr className="text-left font-mono text-xs text-mute"><th className="py-1 font-normal">Date</th><th className="font-normal">District</th><th className="font-normal">Stations</th><th className="font-normal">Detected</th><th className="font-normal">Alert timing</th></tr></thead>
              <tbody>{m.events.map((e, j) => (
                <tr key={j} className="border-t border-line"><td className="py-1 font-mono text-xs">{String(e.event_start)}</td><td>{e.district}</td><td className="font-mono">{e.stations}</td>
                  <td className={e.detected ? 'text-brand' : 'text-severe'}>{e.detected ? 'yes' : 'missed'}</td><td className={`font-mono text-xs ${e.lead_time_h != null && e.lead_time_h >= 47 ? 'text-mute' : ''}`}>{leadText(e.lead_time_h)}</td></tr>))}</tbody>
            </table>
          </div>
        </Panel>
            </div>

      {m.external_validation && (
        <Panel title={`External validation · ${xv?.events ?? ''} documented events ${xv?.period ?? ''} (not used in training)`} className="mt-4">
          {xv?.pod_hybrid_alert && <div className="mb-3 grid gap-3 font-mono text-xs md:grid-cols-4">
            <div><div className="label">Hybrid ≥ ALERT</div><span className="text-brand">{podText(xv.pod_hybrid_alert)}</span></div>
            <div><div className="label">ML only</div>{podText(xv.pod_ml_alert)}</div>
            <div><div className="label">Rainfall only</div>{podText(xv.pod_rain_alert)}</div>
            <div><div className="label">By date confidence</div>{Object.entries(xv.by_confidence ?? {}).map(([k2, p]) => <div key={k2}>{k2}: {p.detected}/{p.n}</div>)}</div>
          </div>}
          {xv?.alert_burden && <p className="mb-3 text-[11px] text-mute">Alert burden (false-alarm proxy, a true FAR needs a complete event list): ALERT district-days per monsoon, with the share within ±2 days of a documented event: {xv.alert_burden.map(b => `${b.monsoon}: ${b.alert_district_days} (${pct(b.share_near_event)})`).join(' · ')}.</p>}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="text-left font-mono text-xs text-mute">
                <th className="py-1 font-normal">Date</th><th className="font-normal">District · place</th><th className="font-normal">Confidence</th><th className="font-normal">Gauges</th>
                <th className="font-normal">Hybrid ≥ ALERT</th><th className="font-normal">ML only</th><th className="font-normal">Rain only</th><th className="font-normal">Peak tier</th><th className="font-normal">Alert timing</th><th className="font-normal">Source</th></tr></thead>
              <tbody>{m.external_validation.events.map(e => {
                const yn = (v: boolean | null) => v == null ? <span className="text-mute">no data</span> : v ? <span className="text-brand">yes</span> : <span className="text-severe">no</span>
                return (<tr key={e.event_id} className="border-t border-line">
                  <td className="py-1.5 font-mono text-xs">{e.date}</td><td>{e.district}{e.place ? <span className="text-mute"> · {e.place}</span> : null}</td>
                  <td className="font-mono text-xs text-mute">{e.date_confidence ?? '—'}{e.sources ? ` · ${e.sources.replaceAll(';', '+')}` : ''}</td>
                  <td className="font-mono">{e.stations_reporting}</td><td>{yn(e.hybrid_alert)}</td><td>{yn(e.ml_alert)}</td><td>{yn(e.rain_alert)}</td>
                  <td className="font-mono text-xs">{e.max_tier}{e.trigger_at_max && e.trigger_at_max !== 'none' ? <span className="text-mute"> ({e.trigger_at_max})</span> : null}</td>
                  <td className={`font-mono text-xs ${e.lead_h_to_day_end != null && e.lead_h_to_day_end >= 47 ? 'text-mute' : ''}`}>{leadText(e.lead_h_to_day_end)}</td>
                  <td><a href={e.source_url} target="_blank" rel="noreferrer" className="text-water hover:underline">link</a></td></tr>)
              })}</tbody>
            </table>
          </div>
          <p className="mt-2 text-[11px] text-mute">Built from SANDRP, Sphere India situation reports, EM-DAT and a curated news list (scripts/build_labels.py); the same district within ±1 day is merged into one event. Only reported disasters appear, so this measures detection, not false alarms. "No data" = no rain gauge in that district was reporting at the time. "Already on" = the gauge was at ALERT from the start of the 48 h window (largely its district baseline), so it is not counted as an early warning.</p>
        </Panel>
      )}
    </div>
  )
}
