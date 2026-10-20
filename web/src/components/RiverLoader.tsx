import { useEffect, useId, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { usePending } from '../lib/data'

// river centreline running from the far end (top) to the viewer (bottom), drawn on the tilted ground plane
const RIVER = 'M60 -20 C 25 30, 95 80, 60 130 S 25 230, 60 280 S 95 380, 60 430'

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
      {/* flat card; only the river is 3-D: it lies on a ground plane tilted away from the viewer, so it starts tiny at
          the horizon and widens as it flows towards the screen */}
      <div className="card-in relative flex flex-col items-center rounded-3xl px-10 pb-7 pt-8">
        <div className="glass-strong absolute inset-0 -z-10 rounded-3xl shadow-[0_40px_90px_rgba(0,0,0,.55)]" />
        <div className="river-stage">
          <div className="river-3d">
            <svg viewBox="0 0 120 400" width="100%" height="100%" preserveAspectRatio="none" aria-hidden style={{ overflow: 'visible', display: 'block' }}>
              <defs>
                <linearGradient id={`${id}-water`} x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0" stopColor="#1f6fbf" stopOpacity=".95" /><stop offset=".5" stopColor="#7fd0ff" stopOpacity=".95" /><stop offset="1" stopColor="#1f6fbf" stopOpacity=".95" />
                </linearGradient>
                {/* light sweeping downstream, i.e. towards the viewer */}
                <linearGradient id={`${id}-sheen`} x1="0" y1="0" x2="0" y2="1" gradientUnits="userSpaceOnUse">
                  <stop offset="0" stopColor="#fff" stopOpacity="0" /><stop offset=".5" stopColor="#fff" stopOpacity=".5" /><stop offset="1" stopColor="#fff" stopOpacity="0" />
                  <animateTransform attributeName="gradientTransform" type="translate" from="0 -400" to="0 400" dur="1.8s" repeatCount="indefinite" />
                </linearGradient>
              </defs>
              <path d={RIVER} fill="none" stroke="#1d4d2b" strokeOpacity=".9" strokeWidth="58" strokeLinecap="round" />
              <path d={RIVER} fill="none" stroke="#a3e635" strokeOpacity=".22" strokeWidth="46" strokeLinecap="round" />
              <path d={RIVER} fill="none" stroke="#0b3d6b" strokeWidth="32" strokeLinecap="round" />
              <path d={RIVER} fill="none" stroke={`url(#${id}-water)`} strokeWidth="26" strokeLinecap="round" />
              <path d={RIVER} fill="none" stroke={`url(#${id}-sheen)`} strokeWidth="26" strokeLinecap="round" />
              <path d={RIVER} fill="none" stroke="#e8fbff" strokeOpacity=".7" strokeWidth="2" strokeLinecap="round" className="flow" style={{ strokeDasharray: '18 34' }} />
              <path d={RIVER} fill="none" stroke="#e8fbff" strokeOpacity=".5" strokeWidth="1.4" strokeLinecap="round" className="flow flow-b" transform="translate(-7 0)" style={{ strokeDasharray: '8 22' }} />
              <path d={RIVER} fill="none" stroke="#e8fbff" strokeOpacity=".5" strokeWidth="1.4" strokeLinecap="round" className="flow flow-c" transform="translate(7 0)" style={{ strokeDasharray: '12 40' }} />
            </svg>
          </div>
        </div>
        <div className="z-lift mt-5 font-display text-3xl leading-none tracking-[.25em] text-white drop-shadow-[0_6px_14px_rgba(0,0,0,.6)]">PRAHAR</div>
        <div className="z-lift mt-2 font-mono text-[11px] uppercase tracking-[.25em] text-ink/75">{label}<span className="dots" /></div>
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
