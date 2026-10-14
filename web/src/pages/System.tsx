import { PageHead, Panel } from '../components/ui'
import { useData, type System as S } from '../lib/data'

export default function System() {
  const s = useData<S>('system')
  if (!s) return null
  const up = s.external.filter(e => e.ok).length
  return (
    <div className="mx-auto max-w-6xl p-6">
      <PageHead kicker="09 · Status" title="System" question="Is every data source and service connected, and how fast is it?" />
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title={`External services · ${up}/${s.external.length} up · checked ${s.checked_at.replace('T', ' ')}`}>
          <ul className="divide-y divide-line text-sm">
            {s.external.map(e => (
              <li key={e.name} className="flex items-center justify-between py-2">
                <span className="flex items-center gap-2"><span className={`h-2 w-2 rounded-full ${e.ok ? 'bg-normal' : 'bg-severe'}`} />{e.name.replace(/_/g, ' ')}</span>
                <span className="font-mono text-xs text-mute">{e.ok ? `${e.ms} ms` : e.error ?? `HTTP ${e.status}`}</span>
              </li>))}
          </ul>
        </Panel>
        <Panel title={`PRAHAR API · ${s.local_api_running ? 'running' : 'not running (static mode)'}`}>
          {s.local_api.length ? (
            <ul className="divide-y divide-line text-sm">{s.local_api.map(e => (
              <li key={e.name} className="flex justify-between py-2"><span className="font-mono">{e.name}</span><span className="font-mono text-xs text-mute">{e.ok ? `${e.ms} ms` : 'down'}</span></li>))}</ul>
          ) : <p className="text-sm text-mute">Start it with <code className="font-mono text-ink">uvicorn backend.app:app --port 8000</code> and run the web app with <code className="font-mono text-ink">VITE_API_URL=/api</code>.</p>}
          <div className="label mt-5">Notebook batches</div>
          <ul className="mt-2 space-y-1 text-sm">{s.notebook_runs.map((r, i) => (
            <li key={i} className="flex justify-between"><span>{r.batch}</span><span className={`font-mono text-xs ${r.status === 'ok' ? 'text-normal' : 'text-severe'}`}>{r.status} · {r.seconds}s</span></li>))}</ul>
        </Panel>
      </div>
      <Panel title="Measured latency (p50 / p95, ms) · old path vs new algorithm" className="mt-4">
        <table className="w-full text-sm">
          <thead><tr className="text-left font-mono text-xs text-mute"><th className="py-1 font-normal">Path</th><th className="font-normal">Variant</th><th className="text-right font-normal">p50</th><th className="text-right font-normal">p95</th><th className="text-right font-normal">Payload</th></tr></thead>
          <tbody>{s.latency.map((r, i) => (
            <tr key={i} className={`border-t border-line ${String(r.variant).startsWith('new') ? 'text-brand' : ''}`}>
              <td className="py-1">{r.path}</td><td className="text-mute">{r.variant}</td>
              <td className="text-right font-mono">{r.p50_ms ?? '—'}</td><td className="text-right font-mono">{r.p95_ms ?? '—'}</td>
              <td className="text-right font-mono text-mute">{r.bytes ? `${(Number(r.bytes) / 1e3).toFixed(0)} KB` : ''}</td></tr>))}</tbody>
        </table>
      </Panel>
    </div>
  )
}
