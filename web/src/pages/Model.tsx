import { PageHead, Panel, Bar } from '../components/ui'
import { useData, type ModelData } from '../lib/data'

const PIPE = [
  ['Inputs', ['Rainfall · 47 gauges', 'River discharge · CWC', 'Landslides · GSI', 'Flood history · IMD', 'District indices']],
  ['Prepare', ['QA & cleaning', 'Hourly alignment', 'Station ↔ district join', 'Rolling windows, API']],
  ['Model', ['32-feature fusion', 'XGBoost / RF / LR', 'Time-based split', 'Threshold tuning']],
  ['Outputs', ['24 h flood probability', 'Severity tier', 'Uncertainty (4A)', 'Exposure (impact)']],
] as const

const METRICS = [['ROC-AUC', 'roc_auc'], ['PR-AUC', 'pr_auc'], ['F1', 'f1'], ['Recall', 'recall'], ['Precision', 'precision'], ['Brier', 'brier']] as const

export default function Model() {
  const m = useData<ModelData>('model')
  if (!m) return null
  const loc = m.importance_groups.find(g => g.group.startsWith('Location'))
  const maxImp = m.importance[0].importance
  const d = m.dataset

  return (
    <div className="mx-auto max-w-6xl p-6">
      <PageHead kicker="07 · Provenance" title="Data & Model" question="Where did this prediction come from?" />

      <div className="grid gap-3 md:grid-cols-4">
        {PIPE.map(([stage, items], i) => (
          <div key={stage} className="relative rounded-xl border border-line p-4">
            <div className="font-mono text-xs text-brand">0{i + 1}</div>
            <div className="mt-1 font-display text-2xl uppercase">{stage}</div>
            <ul className="mt-3 space-y-1 text-sm text-mute">{items.map(x => <li key={x}>{x}</li>)}</ul>
            {i < 3 && <span className="absolute -right-3 top-1/2 hidden text-mute md:block">→</span>}
          </div>
        ))}
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.3fr_1fr]">
        <Panel title="Model comparison · validation vs held-out test">
          <div className="overflow-x-auto">
            <table className="w-full font-mono text-sm">
              <thead><tr className="text-left text-mute"><th className="py-2 font-normal">Metric</th>{m.comparison.map(c => <th key={String(c.model)} className="py-2 text-right font-normal">{c.model}</th>)}</tr></thead>
              <tbody>
                {METRICS.map(([label, k]) => (
                  <tr key={k} className="border-t border-line">
                    <td className="py-2 font-sans">{label}</td>
                    {m.comparison.map(c => (
                      <td key={String(c.model)} className="py-2 text-right">
                        {Number(c[`val_${k}`]).toFixed(3)} <span className="text-mute">/ {Number(c[`test_${k}`]).toFixed(3)}</span>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 rounded-lg border border-alert/30 bg-alert/5 p-3 text-sm">
            <b className="text-alert">Honest read:</b> flood labels (IMD inventory) end on {d.label_end.slice(0, 10)}, so only {d.labelled_rows.toLocaleString()} of {d.rows.toLocaleString()} rows
            are labelled ({d.positives} positives). Later hours are replay-only. The single chronological test covers just Aug 2023, so the trustworthy number is
            leave-one-event-out ROC-AUC (below).
          </div>
        </Panel>

        <Panel title="Top features · share of mean |SHAP| (deployed XGBoost)">
          <div className="space-y-2">
            {m.importance.slice(0, 10).map(f => (
              <div key={f.feature}>
                <div className="flex justify-between text-xs"><span className="font-mono">{f.feature}</span><span className="text-mute">{f.group}</span></div>
                <div className="mt-1"><Bar value={f.importance} max={maxImp} color={f.group.startsWith('Location') ? 'var(--color-alert)' : undefined} /></div>
              </div>
            ))}
          </div>
          {loc && <p className="mt-3 text-[11px] text-mute">Latitude/longitude carry {(loc.importance * 100).toFixed(0)}% of the importance (orange): the model partly memorises <i>where</i> floods happened.</p>}
        </Panel>
      </div>

      <Panel title="Leave-one-event-out validation · XGBoost" className="mt-4">
        <div className="overflow-x-auto">
          <table className="w-full font-mono text-sm">
            <thead><tr className="text-left text-mute">{['Inputs', 'Features', 'ROC-AUC (pooled)', 'PR-AUC (pooled)', 'Lift vs base rate', 'Mean / worst episode ROC'].map(h => <th key={h} className="py-2 font-normal">{h}</th>)}</tr></thead>
            <tbody>{m.fusion.map(f => (
              <tr key={f.label} className={`border-t border-line ${f.final ? 'text-brand' : ''}`}>
                <td className="py-2 font-sans">{f.label}{f.final && ' ✓ deployed'}</td><td>{f.features}</td><td>{f.pooled_roc_auc.toFixed(3)}</td>
                <td>{f.pooled_pr_auc.toFixed(3)}</td><td>{(f.pooled_pr_auc / f.base_rate).toFixed(1)}×</td>
                <td>{f.mean_fold_roc_auc.toFixed(2)} / {f.min_fold_roc_auc.toFixed(2)}</td>
              </tr>))}</tbody>
          </table>
        </div>
        <p className="mt-2 text-[11px] text-mute">Each flood episode is held out in turn (±3 days, 7-day buffer from training). {m.fusion[0]?.positives} positives across {m.fusion[0]?.folds} episodes; base rate {((m.fusion[0]?.base_rate ?? 0) * 100).toFixed(1)}%.</p>
      </Panel>

      <Panel title="Data coverage by month · where the sources meet" className="mt-4">
        <div className="overflow-x-auto">
          <div className="grid min-w-[760px] gap-1" style={{ gridTemplateColumns: `120px repeat(${m.coverage.length}, 1fr)` }}>
            {(['rain_stations', 'discharge_gauges', 'flood_events'] as const).map(k => {
              const mx = Math.max(1, ...m.coverage.map(c => c[k]))
              return [<div key={k} className="pr-2 text-right font-mono text-[10px] text-mute">{({ rain_stations: 'rain stations', discharge_gauges: 'discharge gauges', flood_events: 'flood labels' })[k]}</div>,
                ...m.coverage.map(c => {
                  const inA = c.month >= m.windows.A_train_window.start.slice(0, 7) && c.month <= (m.windows.A_train_window.end ?? '').slice(0, 7)
                  return <div key={k + c.month} title={`${c.month}: ${c[k]}`} className={`h-5 rounded-sm ${inA ? 'ring-1 ring-alert/70' : ''}`}
                    style={{ background: c[k] ? `rgba(163,230,53,${0.15 + 0.85 * c[k] / mx})` : '#213c30' }} />
                })]
            })}
            <div />{m.coverage.map((c, i) => <div key={c.month} className="text-center font-mono text-[8px] text-mute">{i % 6 === 0 ? c.month : ''}</div>)}
          </div>
        </div>
        <p className="mt-2 text-[11px] text-mute">Orange outline = training window A ({m.windows.A_train_window.start} → {m.windows.A_train_window.end}): rainfall and flood labels overlap.
          Discharge only overlaps labels in {m.windows.B_all_sources.start.slice(0, 7)} → {m.windows.B_all_sources.end?.slice(0, 7)}; flood labels stop after that, so later months are replay-only until labels are curated.</p>
      </Panel>

      <Panel title={`Normalisation parameters · fitted on train ${m.normalization.fit_window?.start.slice(0, 10) ?? ''} → ${m.normalization.fit_window?.end.slice(0, 10) ?? ''}`} className="mt-4">
        <div className="max-h-72 overflow-y-auto">
          <table className="w-full font-mono text-xs">
            <thead><tr className="text-left text-mute"><th className="py-1 font-normal">Feature</th><th className="font-normal">Method</th><th className="text-right font-normal">Centre</th><th className="text-right font-normal">Scale</th></tr></thead>
            <tbody>{m.normalization.features.map(f => (
              <tr key={f.feature} className="border-t border-line"><td className="py-1">{f.feature}</td><td className="text-mute">{f.method}</td>
                <td className="text-right">{f.center.toFixed(3)}</td><td className="text-right">{f.scale.toFixed(3)}</td></tr>))}</tbody>
          </table>
        </div>
        <p className="mt-2 text-[11px] text-mute">log_robust = (log1p x − median) / IQR · signed_log for values that can be negative · z-score for indices. Saved in results/preprocessing/normalization_params.json and reused by the API.</p>
      </Panel>

      <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-5">
        {[['Rows', d.rows.toLocaleString()], ['Stations', d.stations], ['Districts', d.districts], ['Positives', d.positives], ['Span', `${d.start.slice(0, 7)} → ${d.end.slice(0, 7)}`]].map(([k, v]) => (
          <div key={String(k)} className="rounded-xl border border-line p-3"><div className="label">{k}</div><div className="mt-1 font-mono">{v}</div></div>
        ))}
      </div>
    </div>
  )
}
