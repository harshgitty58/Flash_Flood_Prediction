import { useEffect, useId, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { usePending } from '../lib/data'

// ---- perspective river scene (viewBox 460 x 210, horizon at y = 34) ----------------------------------------------
// Centreline control points from the horizon (t = 0) to the viewer (t = 1); the river meanders and its half-width grows
// with perspective, so it is a thread at the horizon and wider than the card at the front.
const CTRL: [number, number][] = [[300, 34], [262, 62], [318, 100], [210, 148], [236, 222]]
const halfWidth = (t: number) => 3 + 300 * t ** 2.1
function centre(t: number): [number, number] {           // Catmull-Rom through CTRL
  const n = CTRL.length - 1, f = Math.min(t * n, n - 1e-6), i = Math.floor(f), u = f - i
  const p0 = CTRL[Math.max(i - 1, 0)], p1 = CTRL[i], p2 = CTRL[i + 1], p3 = CTRL[Math.min(i + 2, n)]
  const cr = (a: number, b: number, c: number, d: number) => 0.5 * (2 * b + (c - a) * u + (2 * a - 5 * b + 4 * c - d) * u * u + (3 * b - a - 3 * c + d) * u * u * u)
  return [cr(p0[0], p1[0], p2[0], p3[0]), cr(p0[1], p1[1], p2[1], p3[1])]
}
const T = Array.from({ length: 61 }, (_, i) => i / 60)
const bank = (side: number) => T.map(t => { const [x, y] = centre(t); return [x + side * halfWidth(t), y] as [number, number] })
const pts = (a: [number, number][]) => a.map(([x, y]) => `${x.toFixed(1)} ${y.toFixed(1)}`).join(' L ')
const LEFT = bank(-1), RIGHT = bank(1)
const WATER = `M ${pts(LEFT)} L ${pts([...RIGHT].reverse())} Z`
const SHORE_L = `M ${pts(LEFT)}`, SHORE_R = `M ${pts(RIGHT)}`
const lane = (k: number) => `M ${pts(T.map(t => { const [x, y] = centre(t); return [x + k * halfWidth(t), y] as [number, number] }))}`
// ripples (rings) and glints that ride a lane of the river from the horizon to the viewer, growing as they approach
const RIPPLES = [
  { kind: 'ring', k: -0.45, s: 2.4, d: 0 }, { kind: 'glint', k: 0.3, s: 2.6, d: 0.4 }, { kind: 'ring', k: 0.6, s: 2.2, d: 0.8 },
  { kind: 'glint', k: -0.15, s: 2.8, d: 1.2 }, { kind: 'ring', k: 0.1, s: 2.6, d: 1.6 }, { kind: 'glint', k: -0.6, s: 2.3, d: 2.0 },
  { kind: 'ring', k: 0.4, s: 2.3, d: 2.4 },
].map(r => ({ ...r, path: lane(r.k) }))
// trees on the banks: [x, y, radius]; far ones are small, near ones large
const TREES: [number, number, number][] = [[250, 44, 5], [345, 46, 6], [205, 70, 8], [380, 78, 10], [120, 110, 15], [420, 128, 18], [30, 170, 28], [450, 196, 30]]
const RAIN = Array.from({ length: 30 }, (_, i) => ({ x: (i * 97) % 470, y: (i * 53) % 190 - 20, d: ((i * 37) % 100) / 100 }))

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
          {/* painted perspective scene: banks diverge from a point on the horizon, so the river widens towards the viewer;
              ripples and glints start tiny at the horizon and grow and speed up as they approach (no lane-like dashes) */}
          <svg viewBox="0 0 460 210" width="100%" height="100%" preserveAspectRatio="xMidYMax slice" aria-hidden style={{ display: 'block' }}>
            <defs>
              <linearGradient id={`${id}-sky`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#bfe6fb" /><stop offset="1" stopColor="#e9f7ff" /></linearGradient>
              <linearGradient id={`${id}-grass`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#7fb85a" /><stop offset="1" stopColor="#3f8a34" /></linearGradient>
              <linearGradient id={`${id}-water`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="#e3f6ff" /><stop offset=".3" stopColor="#8fd3f5" /><stop offset=".7" stopColor="#3d9be0" /><stop offset="1" stopColor="#1f6fbf" />
              </linearGradient>
              <radialGradient id={`${id}-tree`} cx=".4" cy=".35" r=".7"><stop offset="0" stopColor="#9be05a" /><stop offset="1" stopColor="#2f7a2c" /></radialGradient>
            </defs>
            <rect width="460" height="34" fill={`url(#${id}-sky)`} />
            <path d="M0 34 Q 60 18 130 30 T 260 28 T 380 24 T 460 32 L460 40 L0 40 Z" fill="#8fbf8a" opacity=".8" />
            <rect y="34" width="460" height="176" fill={`url(#${id}-grass)`} />
            <path d={WATER} fill={`url(#${id}-water)`} />
            {/* soft foam along the shorelines (not kerbs) */}
            <path d={SHORE_L} fill="none" stroke="#f4fbff" strokeOpacity=".55" strokeWidth="2.2" strokeLinejoin="round" />
            <path d={SHORE_R} fill="none" stroke="#f4fbff" strokeOpacity=".55" strokeWidth="2.2" strokeLinejoin="round" />
            {/* sky reflection down the middle of the channel */}
            <path d={lane(0)} fill="none" stroke="#ffffff" strokeOpacity=".16" strokeWidth="26" strokeLinecap="round" />
            {RIPPLES.map((r, i) => (
              <g key={i} opacity="0">
                <animate attributeName="opacity" values="0;.95;.85;0" keyTimes="0;.15;.8;1" dur="2.8s" begin={`${r.d}s`} repeatCount="indefinite" />
                <animateMotion path={r.path} dur="2.8s" begin={`${r.d}s`} repeatCount="indefinite" calcMode="spline" keyTimes="0;1" keySplines=".6 0 .9 .5" />
                <g>
                  <animateTransform attributeName="transform" type="scale" from=".05" to={String(r.s)} dur="2.8s" begin={`${r.d}s`} repeatCount="indefinite" calcMode="spline" keyTimes="0;1" keySplines=".6 0 .9 .5" />
                  {r.kind === 'ring'
                    ? <><ellipse rx="15" ry="4.2" fill="none" stroke="#f4fbff" strokeWidth="1.3" /><ellipse rx="7.5" ry="2" fill="none" stroke="#f4fbff" strokeOpacity=".8" strokeWidth="1" /></>
                    : <path d="M-20 0 q 10 -3.5 20 0 t 20 0" fill="none" stroke="#ffffff" strokeWidth="1.5" strokeLinecap="round" />}
                </g>
              </g>))}
            {TREES.map(([x, y, r], i) => (
              <g key={i}>
                <rect x={x - r * 0.12} y={y - r * 0.2} width={r * 0.24} height={r * 0.9} fill="#6b4a2b" />
                <circle cx={x} cy={y - r * 0.8} r={r} fill={`url(#${id}-tree)`} />
                <circle cx={x - r * 0.6} cy={y - r * 0.45} r={r * 0.65} fill={`url(#${id}-tree)`} />
                <circle cx={x + r * 0.6} cy={y - r * 0.45} r={r * 0.65} fill={`url(#${id}-tree)`} />
              </g>))}
            {RAIN.map((r, i) => <line key={i} className="rain" x1={r.x} y1={r.y} x2={r.x - 4} y2={r.y + 12} stroke="#ffffff" strokeOpacity=".5" strokeWidth="1" style={{ animationDelay: `${r.d}s` }} />)}
          </svg>
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
