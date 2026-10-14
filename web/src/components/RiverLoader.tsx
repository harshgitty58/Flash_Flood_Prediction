import { useEffect, useId, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { usePending } from '../lib/data'

// horizontal meandering centreline, 320 units wide (rendered at 320 px ≈ 8.5 cm)
const RIVER = 'M-10 36 C 30 16, 70 56, 110 36 S 190 16, 230 36 S 300 56, 330 36'

/** Translucent overlay with a small flowing-river box. Appears only if work lasts longer than `delay` ms. */
export function RiverOverlay({ active, delay = 200, label = 'Loading layers', leaving = false, passive = false }: { active: boolean; delay?: number; label?: string; leaving?: boolean; passive?: boolean }) {
  const [show, setShow] = useState(false)
  const id = useId().replace(/:/g, '')
  useEffect(() => {
    if (!active) { setShow(false); return }
    const t = setTimeout(() => setShow(true), delay)
    return () => clearTimeout(t)
  }, [active, delay])
  if (!show) return null
  return (
    <div className={`fixed inset-0 z-50 grid place-items-center bg-bg/45 backdrop-blur-md ${leaving ? 'fade-out' : ''} ${passive ? 'pointer-events-none' : ''}`} style={{ animation: 'fadein .2s ease both' }} role="status" aria-live="polite">
      <div className="glass-strong flex flex-col items-center rounded-3xl px-8 pb-5 pt-6 shadow-2xl">
        <svg viewBox="0 0 320 72" width={320} height={72} aria-hidden style={{ overflow: 'visible' }}>
          <defs>
            <linearGradient id={`${id}-water`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#bdf0ff" stopOpacity=".95" /><stop offset=".5" stopColor="#4fb3f0" stopOpacity=".9" /><stop offset="1" stopColor="#1f6fbf" stopOpacity=".9" />
            </linearGradient>
            {/* fade the river in and out at both ends so it seems to flow from and into nothing */}
            <linearGradient id={`${id}-fade`} x1="0" y1="0" x2="1" y2="0">
              <stop offset="0" stopColor="#fff" stopOpacity="0" /><stop offset=".12" stopColor="#fff" stopOpacity="1" />
              <stop offset=".88" stopColor="#fff" stopOpacity="1" /><stop offset="1" stopColor="#fff" stopOpacity="0" />
            </linearGradient>
            <mask id={`${id}-mask`}><rect x="-10" y="0" width="340" height="72" fill={`url(#${id}-fade)`} /></mask>
            {/* moving highlight that sweeps downstream */}
            <linearGradient id={`${id}-sheen`} x1="0" y1="0" x2="1" y2="0" gradientUnits="userSpaceOnUse">
              <stop offset="0" stopColor="#fff" stopOpacity="0" /><stop offset=".5" stopColor="#fff" stopOpacity=".55" /><stop offset="1" stopColor="#fff" stopOpacity="0" />
              <animateTransform attributeName="gradientTransform" type="translate" from="-320 0" to="320 0" dur="1.6s" repeatCount="indefinite" />
            </linearGradient>
          </defs>
          <g mask={`url(#${id}-mask)`}>
            <path d={RIVER} fill="none" stroke="#4fb3f0" strokeOpacity=".18" strokeWidth="26" strokeLinecap="round" />
            <path d={RIVER} fill="none" stroke={`url(#${id}-water)`} strokeWidth="16" strokeLinecap="round" />
            <path d={RIVER} fill="none" stroke={`url(#${id}-sheen)`} strokeWidth="16" strokeLinecap="round" />
            <path d={RIVER} fill="none" stroke="#e8fbff" strokeOpacity=".55" strokeWidth="1.4" strokeLinecap="round" className="flow" style={{ strokeDasharray: '22 30' }} />
            <path d={RIVER} fill="none" stroke="#e8fbff" strokeOpacity=".4" strokeWidth="1" strokeLinecap="round" className="flow flow-b" transform="translate(0 -4.5)" style={{ strokeDasharray: '8 18' }} />
            <path d={RIVER} fill="none" stroke="#e8fbff" strokeOpacity=".35" strokeWidth="1" strokeLinecap="round" className="flow flow-c" transform="translate(0 4.5)" style={{ strokeDasharray: '12 40' }} />
          </g>
        </svg>
        <div className="mt-4 font-display text-xl leading-none tracking-[.2em] text-white">PRAHAR</div>
        <div className="mt-1.5 font-mono text-[10px] uppercase tracking-[.25em] text-ink/70">{label}<span className="dots" /></div>
      </div>
    </div>
  )
}

/** Global overlay driven by in-flight data fetches. */
export default function DataLoader() {
  return <RiverOverlay active={usePending() > 0} />
}

/** Brand transition on every route change: always shown for `ms`, then fades out — independent of load time. */
export function RouteTransition({ ms = 700 }: { ms?: number }) {
  const { pathname } = useLocation()
  const [phase, setPhase] = useState<'on' | 'leaving' | 'off'>('on')
  const first = useRef(true)
  useEffect(() => {
    setPhase('on')
    const total = first.current ? ms + 300 : ms  // a little longer on first load (brand splash)
    first.current = false
    const a = setTimeout(() => setPhase('leaving'), total - 220)
    const b = setTimeout(() => setPhase('off'), total)
    return () => { clearTimeout(a); clearTimeout(b) }
  }, [pathname, ms])
  return <RiverOverlay active={phase !== 'off'} delay={0} leaving={phase === 'leaving'} passive label={pathname === '/' ? 'Predict · Prepare · Protect' : 'Loading view'} />
}
