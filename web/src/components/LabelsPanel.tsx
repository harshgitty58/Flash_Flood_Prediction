import type { Metrics } from '../lib/data'
import { Panel } from './ui'

const f = (v: number | null | undefined, d = 3) => (v == null ? '—' : v.toFixed(d))
const SRC: Record<string, string> = { imd: 'IMD inventory', sandrp: 'SANDRP', sphere: 'Sphere India SitReps', emdat: 'EM-DAT', curated: 'News (curated)' }

/** Ground truth: where the labels come from, how they were audited, and what fixing them did to the metrics. */
export default function LabelsPanel({ l }: { l: NonNullable<Metrics['labels']> }) {
  const a = l.audit?.summary
  const e = l.experiment
  const grid = e?.xgboost_grid.filter(g => g.trained_on !== 'v2_masked' && g.scored_on !== 'v2_masked') ?? []
  return (
    <Panel title="Ground truth · label sources, audit and what fixing them changed" className="mt-4">
      <div className="grid gap-4 lg:grid-cols-3">
        <div>
          <div className="label mb-2">Documented events 2022–2025</div>
          <div className="font-mono text-3xl font-semibold text-brand">{l.sources?.events ?? '—'}</div>
          <div className="text-[11px] text-mute">{l.sources?.district_days} district-days · {l.sources?.corroborated_events} confirmed by ≥ 2 sources</div>
          <table className="mt-3 w-full font-mono text-xs">
            <tbody>{Object.entries(l.sources?.by_source_family ?? {}).map(([k, v]) => (
              <tr key={k} className="border-t border-line"><td className="py-1 font-sans">{SRC[k] ?? k}</td><td className="text-right">{v} district-days</td></tr>))}</tbody>
          </table>
        </div>
        <div>
          <div className="label mb-2">Label fix: district names (L0)</div>
          <p className="text-xs text-mute">The IMD inventory writes "Rudra Prayag", "Udam Singh Nagar" and "Garhwal". The exact-match join dropped 13 of 29 flood days, so Rudraprayag had 0 positives.</p>
          <table className="mt-2 w-full font-mono text-xs">
            <thead><tr className="text-left text-mute"><th className="py-1 font-normal">Test</th><th className="font-normal">ROC-AUC</th><th className="font-normal">PR-AUC</th><th className="font-normal">F1</th></tr></thead>
            <tbody>{l.before_after?.map(r => (
              <tr key={r.model} className={`border-t border-line ${r.model === 'XGBoost' ? 'text-brand' : ''}`}>
                <td className="py-1 font-sans">{r.model}</td>
                <td>{f(r.roc_auc_before, 2)} → {f(r.roc_auc_after, 2)}</td><td>{f(r.pr_auc_before, 2)} → {f(r.pr_auc_after, 2)}</td><td>{f(r.f1_before, 2)} → {f(r.f1_after, 2)}</td></tr>))}</tbody>
          </table>
        </div>
        <div>
          <div className="label mb-2">Audit: IMD vs SANDRP (2022 – Aug 2023)</div>
          {a && <>
            <div className="font-mono text-3xl font-semibold text-alert">{a.sandrp_only_events}</div>
            <div className="text-[11px] text-mute">damaging events reported by SANDRP but missing from the IMD labels (IMD has {a.imd_events}); {a.sandrp_only_valtest_alerted_by_hybrid} of the val/test ones already got a hybrid ALERT that is scored as a false alarm</div>
          </>}
          <div className="mt-2 max-h-32 overflow-y-auto">
            <table className="w-full font-mono text-xs">
              <thead><tr className="text-left text-mute"><th className="py-1 font-normal">District</th><th className="font-normal">IMD</th><th className="font-normal">SANDRP</th><th className="font-normal">only SANDRP</th></tr></thead>
              <tbody>{l.audit?.by_district.map(r => (
                <tr key={r.district} className="border-t border-line"><td className="py-0.5 font-sans">{r.district}</td><td>{r.imd_days}</td><td>{r.sandrp_days}</td><td className={r.sandrp_only_days ? 'text-alert' : ''}>{r.sandrp_only_days}</td></tr>))}</tbody>
            </table>
          </div>
        </div>
      </div>

      {e && <div className="mt-4 grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <div>
          <div className="label mb-2">Label v2 experiment · XGBoost, test month (trained on × scored against)</div>
          <table className="w-full font-mono text-xs">
            <thead><tr className="text-left text-mute"><th className="py-1 font-normal">Trained on</th><th className="font-normal">Scored on</th><th className="font-normal">PR-AUC</th><th className="font-normal">F1</th><th className="font-normal">Day POD</th><th className="font-normal">Day FAR</th><th className="font-normal">Day CSI [95% CI]</th></tr></thead>
            <tbody>{grid.map(g => (
              <tr key={g.trained_on + g.scored_on} className={`border-t border-line ${g.trained_on === 'v1' ? 'text-brand' : ''}`}>
                <td className="py-1">{g.trained_on}</td><td>{g.scored_on}</td><td>{f(g.pr_auc)}</td><td>{f(g.f1)}</td><td>{f(g.dd_POD, 2)}</td><td>{f(g.dd_FAR, 2)}</td>
                <td>{f(g.dd_CSI)} <span className="text-mute">[{f(g.dd_CSI_ci95?.[0], 2)}, {f(g.dd_CSI_ci95?.[1], 2)}]</span></td></tr>))}</tbody>
          </table>
        </div>
        <div className="text-xs leading-relaxed text-mute">
          <div className="label mb-2">Decision (rule fixed before the run)</div>
          <p>v1 = IMD only; v2 = IMD + SANDRP + situation reports. v2 replaces v1 for training only if the v2-trained model is at least as good on <span className="text-ink">both</span> answer keys and on event-CV.</p>
          <p className="mt-2">Result: <span className={e.decision.adopt_v2 ? 'text-brand' : 'text-alert'}>{e.decision.adopt_v2 ? 'adopted' : 'not adopted for training'}</span>. Event-CV improved (ROC {f(e.event_cv.v1?.pooled_roc_auc, 2)} → {f(e.event_cv.v2?.pooled_roc_auc, 2)}), but on the test month the v2-trained model is worse on both answer keys. Most of the extra events are local cloudbursts that no gauge recorded.</p>
          <p className="mt-2">Used as the answer key, v2 shows the deployed (green) model is better than the official labels say: many of its "false alarms" are real, documented events.</p>
          {l.district_day && <p className="mt-2">District-day model (gauges + USDMA stations + ERA5, every district every day): good ranking (test ROC-AUC {f(l.district_day.test_roc_auc, 2)}, PR-AUC {f(l.district_day.test_pr_auc, 2)} vs base {f(l.district_day.base_rate, 2)}), but with only 18 training flood days its alert threshold is too strict (CSI {f(l.district_day.csi, 2)} vs hybrid {f(l.district_day.hybrid_csi, 2)}; external {l.district_day.external}), so it is {l.district_day.adopted ? 'adopted' : 'not adopted'}.</p>}
          {l.model_upgrade && <p className="mt-2">Model upgrades: the ensemble ranks better (ROC-AUC {f(l.model_upgrade.e1.roc_xgb, 2)} → {f(l.model_upgrade.e1.roc_ens, 2)}) but does not raise CSI. Event-fitted rain thresholds show the median documented flood had only ~{f(l.model_upgrade.e2.median_event_24h, 0)} mm/24 h at the nearest gauge (CSI {f(l.model_upgrade.e2.csi_current, 2)} → {f(l.model_upgrade.e2.csi_fitted, 2)}). The district ranking puts the flooded district in the top 3 for {f(l.model_upgrade.e3.external_model * 100, 0)}% of events (history alone {f(l.model_upgrade.e3.external_prior * 100, 0)}%).</p>}
          {l.rain_rule_tuning && <p className="mt-2">Rainfall-rule re-tuning: {l.rain_rule_tuning.adopted ? 'adopted' : 'no rule beat the IMD default beyond noise, so the default is kept'}.</p>}
        </div>
      </div>}
    </Panel>
  )
}
