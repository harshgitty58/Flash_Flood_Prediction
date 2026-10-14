import { Link } from 'react-router-dom'
import { fmtTime, pct, pretty, TIER_COLOR, type StationSnap } from '../lib/data'
import { Bar, TierBadge } from './ui'

// Observed input values at prediction time. These are signals, not SHAP attributions (Phase 4B).
const SIGNALS: [string, string, string, number][] = [
  ['rain_24h', 'Rain, 24 h', 'mm', 150],
  ['rain_72h', 'Rain, 72 h', 'mm', 300],
  ['rain_max_intensity_24h', 'Peak intensity, 24 h', 'mm/h', 50],
  ['api_decay_85', 'Antecedent precip. index', '', 200],
  ['landslide_count_10km', 'Landslides within 10 km', '', 400],
  ['historical_flood_count_prior_t', 'Prior flood events (district)', '', 40],
  ['district_flood_severity_index', 'District flood severity idx', '', 10],
]

export default function StationDrawer({ s, onClose }: { s: StationSnap; onClose: () => void }) {
  const c = TIER_COLOR[s.tier]
  return (
    <aside className="glass rise absolute right-4 top-4 bottom-4 z-10 flex w-[340px] max-w-[calc(100%-2rem)] flex-col overflow-y-auto rounded-2xl p-5">
      <div className="flex items-start justify-between">
        <div><div className="label">Station · {s.district}</div><h2 className="mt-1 text-2xl font-semibold">{pretty(s.station)}</h2></div>
        <button onClick={onClose} className="text-mute hover:text-ink" aria-label="Close">✕</button>
      </div>
      <div className="mt-5 flex items-end justify-between">
        <div><div className="text-xs text-mute">Calibrated flood probability (24 h)</div><div className="font-mono text-5xl font-semibold" style={{ color: c }}>{pct(s.p)}</div></div>
        <TierBadge tier={s.tier} />
      </div>
      <div className="mt-3"><Bar value={s.p} color={c} /></div>
      <div className="mt-2 font-mono text-[11px] text-mute">raw score {s.raw_score.toFixed(2)} · as of {fmtTime(s.time)} · observed flood: {s.observed == null ? 'unlabelled period' : s.observed ? 'YES' : 'no'}</div>

      {s.trigger && s.trigger !== 'none' && (
        <div className="mt-4 rounded-lg border border-line p-3 text-xs">
          <div className="label mb-1.5">Tier set by</div>
          <div className="flex justify-between"><span className={s.trigger === 'ml' ? 'text-ink' : 'text-mute'}>ML model (calibrated)</span><TierBadge tier={s.tier_ml ?? 'NORMAL'} /></div>
          <div className="mt-1.5 flex justify-between"><span className={s.trigger === 'rainfall' ? 'text-ink' : 'text-mute'}>IMD rainfall threshold</span><TierBadge tier={s.tier_rain ?? 'NORMAL'} /></div>
          <div className="mt-1.5 text-mute">Final tier = the higher of the two{s.trigger === 'rainfall' ? ' · driven by observed rainfall at this gauge' : ''}.</div>
        </div>
      )}

      <div className="mt-6 grid grid-cols-2 gap-2 text-sm">
        <div className="rounded-lg border border-line p-3"><div className="label">Confidence</div><div className="mt-1 font-mono">{pct(s.confidence)}</div></div>
        <div className="rounded-lg border border-line p-3"><div className="label">90% set</div><div className={`mt-1 font-mono ${s.cp_set_90 === 'FLOOD' ? 'text-severe' : s.cp_set_90 === 'UNCERTAIN' ? 'text-alert' : ''}`}>{({ FLOOD: 'Flood', NO_FLOOD: 'No flood', UNCERTAIN: 'Uncertain', EMPTY: '—' })[s.cp_set_90]}</div></div>
      </div>

      {s.drivers.length > 0 && (<>
        <div className="label mt-6">Why this score · top SHAP drivers</div>
        <div className="mt-3 space-y-2.5">
          {s.drivers.map(d => (
            <div key={d.feature}>
              <div className="flex justify-between gap-2 text-xs"><span className="truncate">{d.feature.replace(/_/g, ' ')} <span className="text-mute">= {+d.value.toFixed(2)}</span></span>
                <span className={`font-mono ${d.shap > 0 ? 'text-severe' : 'text-normal'}`}>{d.shap > 0 ? '+' : ''}{d.shap.toFixed(2)}</span></div>
              <div className="mt-1 flex h-1.5 rounded-full bg-line"><div className="h-full w-1/2">{d.shap < 0 && <div className="ml-auto h-full rounded-l-full bg-normal" style={{ width: `${Math.min(100, Math.abs(d.shap) * 100)}%` }} />}</div>
                <div className="h-full w-1/2">{d.shap > 0 && <div className="h-full rounded-r-full bg-severe" style={{ width: `${Math.min(100, d.shap * 100)}%` }} />}</div></div>
            </div>
          ))}
        </div>
      </>)}

      <div className="label mt-6">Input signals at prediction time</div>
      <div className="mt-3 space-y-3">
        {SIGNALS.map(([k, label, unit, max]) => {
          const v = s.signals[k]
          return (
            <div key={k}>
              <div className="flex justify-between text-xs"><span className="text-mute">{label}</span><span className="font-mono">{v == null ? '—' : `${+v.toFixed(1)} ${unit}`}</span></div>
              <div className="mt-1"><Bar value={v ?? 0} max={max} color="var(--color-water)" /></div>
            </div>
          )
        })}
      </div>
      <p className="mt-4 text-[11px] text-mute">SHAP = push on the model's log-odds (red raises, green lowers). Importance, not physical causation.</p>
      <Link to="/app/impact" className="mt-auto rounded-full border border-line py-2 text-center text-sm hover:border-ink">See exposure around this station →</Link>
    </aside>
  )
}
