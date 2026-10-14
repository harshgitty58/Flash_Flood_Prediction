import type { ReactNode } from 'react'
import { TIER_COLOR, type Tier } from '../lib/data'

export function Panel({ title, right, children, className = '' }: { title?: string; right?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`glass rounded-xl p-4 ${className}`}>
      {title && <header className="mb-3 flex items-center justify-between"><h3 className="label">{title}</h3>{right}</header>}
      {children}
    </section>
  )
}

export function Stat({ label, value, sub, color }: { label: string; value: ReactNode; sub?: ReactNode; color?: string }) {
  return (
    <div className="glass rounded-xl p-4">
      <div className="label">{label}</div>
      <div className="mt-2 font-mono text-3xl font-semibold" style={{ color }}>{value}</div>
      {sub && <div className="mt-1 text-xs text-mute">{sub}</div>}
    </div>
  )
}

export function TierBadge({ tier }: { tier: Tier }) {
  const c = TIER_COLOR[tier]
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 font-mono text-[11px] font-semibold tracking-widest"
      style={{ color: c, background: `${c}1f`, border: `1px solid ${c}55` }}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: c }} />{tier}
    </span>
  )
}

export function Bar({ value, max = 1, color = 'var(--color-water)' }: { value: number; max?: number; color?: string }) {
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-line">
      <div className="h-full rounded-full transition-all duration-700" style={{ width: `${Math.min(100, (value / max) * 100)}%`, background: color }} />
    </div>
  )
}

export function Pending({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-line p-5">
      <div className="label text-alert!">◌ Pending module</div>
      <div className="mt-2 font-semibold">{title}</div>
      <div className="mt-1 text-sm text-mute">{children}</div>
    </div>
  )
}

export function PageHead({ kicker, title, question }: { kicker: string; title: string; question: string }) {
  return (
    <div className="mb-6">
      <div className="label">{kicker}</div>
      <h1 className="mt-1 font-display text-5xl uppercase tracking-wide">{title}</h1>
      <p className="mt-1 text-mute">{question}</p>
    </div>
  )
}

export function BasemapSwitch({ value, onChange, is3d, on3d }: { value: string; onChange: (v: 'dark' | 'satellite' | 'terrain') => void; is3d: boolean; on3d: (v: boolean) => void }) {
  return (
    <div className="glass flex items-center gap-1 rounded-full p-1 font-mono text-[11px] uppercase tracking-wider">
      {(['dark', 'satellite', 'terrain'] as const).map(b => (
        <button key={b} onClick={() => onChange(b)} className={`rounded-full px-3 py-1.5 transition ${value === b ? 'bg-ink text-bg' : 'text-mute hover:text-ink'}`}>{b}</button>
      ))}
      <span className="mx-1 h-4 w-px bg-line" />
      <button onClick={() => on3d(!is3d)} className={`rounded-full px-3 py-1.5 transition ${is3d ? 'bg-water text-bg' : 'text-mute hover:text-ink'}`}>3D</button>
    </div>
  )
}
