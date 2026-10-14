import { Bar as RBar, BarChart, Cell, LabelList, ResponsiveContainer, XAxis, YAxis } from 'recharts'
import { PageHead, Panel } from '../components/ui'
import { pct, useData, type ModelData, type Snapshot } from '../lib/data'

const STATUS = { available: ['✓', 'text-normal'], missing: ['✕', 'text-severe'], pending: ['◌', 'text-mute'] } as const

export default function Uncertainty() {
  const snap = useData<Snapshot>('snapshot')
  const model = useData<ModelData>('model')
  if (!snap || !model) return null

  const xgb = model.fusion.slice(0, 5) // cumulative A→E; F (no lat/lon) is a side variant shown on the Model page
  const jumps = xgb.slice(1).map((f, i) => ({ label: f.label, gain: f.pooled_roc_auc - xgb[i].pooled_roc_auc }))
  const biggest = jumps.reduce((a, b) => (b.gain > a.gain ? b : a))
  const final = model.fusion.find(f => f.final) ?? xgb[xgb.length - 1]

  return (
    <div className="mx-auto max-w-6xl p-6">
      <PageHead kicker="05 · Trust" title="Uncertainty" question="How much can we trust the prediction?" />

      <div className="grid gap-4 lg:grid-cols-[1fr_1.4fr]">
        <Panel title="Source health at replay time">
          <ul className="divide-y divide-line">
            {snap.sources.map(s => {
              const [icon, cls] = STATUS[s.status]
              return (
                <li key={s.name} className="flex items-center justify-between py-2.5">
                  <div><div className="text-sm">{s.name}</div><div className="text-xs text-mute">{s.detail}</div></div>
                  <span className={`font-mono text-xs uppercase ${cls}`}>{icon} {s.status}</span>
                </li>
              )
            })}
          </ul>
        </Panel>

        <Panel title="What each data source adds · XGBoost, leave-one-event-out ROC-AUC">
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={xgb} layout="vertical" margin={{ left: 20, right: 48 }}>
                <XAxis type="number" domain={[0, 1]} hide />
                <YAxis type="category" dataKey="label" width={140} tick={{ fontSize: 12, fill: '#f1f8f3' }} axisLine={false} tickLine={false} />
                <RBar dataKey="pooled_roc_auc" radius={[0, 4, 4, 0]} barSize={18}>
                  {xgb.map((f, i) => <Cell key={i} fill={f.final ? '#a3e635' : '#4fb3f0'} fillOpacity={0.35 + (0.65 * i) / (xgb.length - 1)} />)}
                  <LabelList dataKey="pooled_roc_auc" position="right" formatter={(v) => Number(v).toFixed(2)} style={{ fill: '#f1f8f3', fontSize: 12, fontFamily: 'JetBrains Mono' }} />
                </RBar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 rounded-lg border border-water/30 bg-water/5 p-3 text-sm">
            Largest single gain comes from adding <b>{biggest.label.replace('+ ', '').toLowerCase()}</b> (+{biggest.gain.toFixed(2)} ROC-AUC).
            Rainfall alone scores {xgb[0].pooled_roc_auc.toFixed(2)}; the deployed model ({final.label.replace('+ ', '')}) reaches {final.pooled_roc_auc.toFixed(2)} across {final.folds} held-out flood episodes.
          </div>
          <p className="mt-2 text-[11px] text-mute">Each bar is a model trained with that cumulative set of inputs and tested on flood episodes it never saw (src/event_cv.py). Green = deployed model.</p>
        </Panel>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <Panel title="Conformal coverage on held-out test month">
          <table className="w-full font-mono text-sm">
            <thead><tr className="text-left text-mute"><th className="py-1 font-normal">Target</th><th className="font-normal">All</th><th className="font-normal">Flood</th><th className="font-normal">No flood</th><th className="font-normal">"Uncertain"</th></tr></thead>
            <tbody>{snap.conformal.coverage.map(c => (
              <tr key={c.nominal} className="border-t border-line"><td className="py-1">{pct(c.nominal)}</td><td>{pct(c.coverage_all, 1)}</td>
                <td>{pct(c.coverage_flood)}</td><td>{pct(c.coverage_no_flood, 1)}</td><td>{pct(c.share_uncertain)}</td></tr>))}</tbody>
          </table>
          <p className="mt-2 text-[11px] text-mute">Venn-Abers calibration + class-conditional conformal sets, calibrated on {snap.conformal.calibration_positives} validation floods,
            tested on {snap.conformal.test_positives}. Brier {snap.conformal.brier_raw} → {snap.conformal.brier_calibrated} after calibration. A high "uncertain" share is the model saying it cannot separate the classes confidently.</p>
        </Panel>
        <Panel title="What if a data source fails? · inference-time degradation">
          <table className="w-full text-sm">
            <thead><tr className="text-left font-mono text-xs text-mute"><th className="py-1 font-normal">Scenario</th><th className="font-normal">ROC-AUC</th><th className="font-normal">PR-AUC</th></tr></thead>
            <tbody>{model.robustness.map(r => {
              const b = model.robustness[0]; const bad = r.pr_auc < b.pr_auc * 0.5
              return (<tr key={r.scenario} className="border-t border-line"><td className="py-1">{r.scenario}</td>
                <td className="font-mono">{r.roc_auc.toFixed(2)}</td>
                <td className={`font-mono ${bad ? 'text-severe' : ''}`}>{r.pr_auc.toFixed(3)}{r.kind !== 'baseline' && <span className="ml-1 text-[10px] text-mute">({(r.pr_auc / b.pr_auc).toFixed(1)}×)</span>}</td></tr>)
            })}</tbody>
          </table>
          <p className="mt-2 text-[11px] text-mute">Deployed model, no retraining; missing inputs fall back to training medians. Red = PR-AUC more than halved. Rare-event skill (PR-AUC) depends most on flood-history records and rainfall gauges.</p>
        </Panel>
      </div>
    </div>
  )
}
