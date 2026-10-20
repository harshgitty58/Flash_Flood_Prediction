import { Link } from 'react-router-dom'
import { useData, type Metrics } from '../lib/data'

const f = (v: number | null | undefined, d = 2) => (v == null ? '—' : v.toFixed(d))
const ci = (c?: [number | null, number | null]) => (c ? `95 % CI ${f(c[0])}–${f(c[1])}` : '')

// Headline verification on held-out data, read from the exported metrics (numbers are never typed by hand).
export default function VerifiedResults() {
  const m = useData<Metrics>('metrics')
  const v = m?.verification
  if (!v) return null
  const dd = (layer: string) => v.contingency.find(r => r.unit === 'district-day' && r.split === 'test' && r.level === '≥ ALERT' && r.layer === layer)
  const hyb = dd('hybrid (deployed)'), prior = dd('district prior only'), pers = dd('persistence (flood yesterday)')
  const xv = m.external_validation?.summary
  const p = v.probabilistic['station-hour'], lt = v.lead_time
  const items: [string, string, string][] = [
    [f(hyb?.CSI, 3), 'district-day CSI at ≥ ALERT, Aug 2023 test',
      `POD ${f(hyb?.POD)} · FAR ${f(hyb?.FAR)} · ${ci(hyb?.ci95?.CSI)} · baselines: district prior ${f(prior?.CSI, 3)}, persistence ${f(pers?.CSI, 3)}`],
    [xv?.pod_hybrid_alert ? `${xv.pod_hybrid_alert.detected}/${xv.pod_hybrid_alert.n}` : '—', 'documented floods caught after training ended',
      xv?.pod_hybrid_alert ? `POD ${f(xv.pod_hybrid_alert.POD)} · ${ci(xv.pod_hybrid_alert.ci95)} · events ${xv.period ?? ''}, never used in training` : ''],
    [f(p.BSS, 3), 'Brier skill score vs monthly climatology', `ECE ${f(v.probabilistic.ECE_station_hour, 3)}: calibrated probabilities match observed frequencies`],
    [`${lt.warned_before}/${lt.events}`, 'events warned before the event day',
      `median lead ${lt.median_lead_h ?? '—'} h · ${lt.baseline_only} already on as a district baseline · ${lt.missed} missed`],
  ]
  return (
    <div className="rounded-2xl border border-brand/40 bg-black/55 p-6 backdrop-blur md:p-8">
      <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-brand">Verified on held-out floods · WMO-style scores</div>
      <h3 className="mt-1 font-display text-3xl text-ink md:text-4xl">What the warnings actually achieved</h3>
      <p className="mt-1 text-sm text-ink/75">Scored on months and events the model never saw, against the same baselines a forecaster would use. Gauges miss many local cloudbursts, so these are honest, modest numbers.</p>
      <div className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-4">
        {items.map(([val, label, sub]) => (
          <div key={label} className="rounded-xl border border-line bg-black/30 p-3">
            <div className="font-mono text-3xl text-brand">{val}</div>
            <div className="text-sm text-ink/85">{label}</div>
            <div className="mt-1 text-[11px] text-mute">{sub}</div>
          </div>))}
      </div>
      <Link to="/app/metrics" className="mt-4 inline-block rounded-full bg-brand px-5 py-2 text-sm font-semibold text-bg hover:brightness-110">See every metric →</Link>
    </div>
  )
}
