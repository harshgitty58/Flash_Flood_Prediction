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
      <div style={{ perspective: 1100 }}>
      <div className="card3d relative flex flex-col items-center rounded-3xl px-10 pb-7 pt-9">
        {/* glass on its own layer: backdrop-filter would flatten the 3-D children */}
        <div className="glass-strong absolute inset-0 -z-10 rounded-3xl shadow-[0_40px_90px_rgba(0,0,0,.55)]" />
        <div className="river-plane" style={{ width: 'min(480px, 80vw)' }}>
        <svg viewBox="0 0 320 72" width="100%" aria-hidden style={{ overflow: 'visible', display: 'block' }}>
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
            {/* banks and riverbed depth: green valley sides + a darker underlayer give the channel thickness */}
            <path d={RIVER} fill="none" stroke="#2f6b3a" strokeOpacity=".55" strokeWidth="40" strokeLinecap="round" transform="translate(0 6)" />
            <path d={RIVER} fill="none" stroke="#a3e635" strokeOpacity=".16" strokeWidth="34" strokeLinecap="round" />
            <path d={RIVER} fill="none" stroke="#0b3d6b" strokeOpacity=".85" strokeWidth="18" strokeLinecap="round" transform="translate(0 3.5)" />
            <path d={RIVER} fill="none" stroke="#4fb3f0" strokeOpacity=".18" strokeWidth="26" strokeLinecap="round" />
            <path d={RIVER} fill="none" stroke={`url(#${id}-water)`} strokeWidth="16" strokeLinecap="round" />
            <path d={RIVER} fill="none" stroke={`url(#${id}-sheen)`} strokeWidth="16" strokeLinecap="round" />
            <path d={RIVER} fill="none" stroke="#e8fbff" strokeOpacity=".55" strokeWidth="1.4" strokeLinecap="round" className="flow" style={{ strokeDasharray: '22 30' }} />
            <path d={RIVER} fill="none" stroke="#e8fbff" strokeOpacity=".4" strokeWidth="1" strokeLinecap="round" className="flow flow-b" transform="translate(0 -4.5)" style={{ strokeDasharray: '8 18' }} />
            <path d={RIVER} fill="none" stroke="#e8fbff" strokeOpacity=".35" strokeWidth="1" strokeLinecap="round" className="flow flow-c" transform="translate(0 4.5)" style={{ strokeDasharray: '12 40' }} />
          </g>
        </svg>
        </div>
        <div className="z-lift mt-5 font-display text-3xl leading-none tracking-[.25em] text-white drop-shadow-[0_6px_14px_rgba(0,0,0,.6)]">PRAHAR</div>
        <div className="z-lift mt-2 font-mono text-[11px] uppercase tracking-[.25em] text-ink/75">{label}<span className="dots" /></div>
      </div>
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
