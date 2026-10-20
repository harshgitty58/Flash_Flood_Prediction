import { lazy, StrictMode, Suspense } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './index.css'
import AppShell from './pages/AppShell'
import Landing from './pages/Landing'
const Model = lazy(() => import('./pages/Model'))
const Overview = lazy(() => import('./pages/Overview'))
const RiskMap = lazy(() => import('./pages/RiskMap'))
const Impact = lazy(() => import('./pages/Impact'))
const Forecast = lazy(() => import('./pages/Secondary').then(m => ({ default: m.Forecast })))
const Events = lazy(() => import('./pages/Secondary').then(m => ({ default: m.Events })))
import DataLoader, { RiverOverlay, RouteTransition } from './components/RiverLoader'
const Uncertainty = lazy(() => import('./pages/Uncertainty'))
const Metrics = lazy(() => import('./pages/Metrics'))
const System = lazy(() => import('./pages/System'))

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <RouteTransition />
      <DataLoader />
      <Suspense fallback={<RiverOverlay active label="Loading view" />}>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/app" element={<AppShell />}>
          <Route index element={<Navigate to="overview" replace />} />
          <Route path="overview" element={<Overview />} />
          <Route path="forecast" element={<Forecast />} />
          <Route path="map" element={<RiskMap />} />
          <Route path="impact" element={<Impact />} />
          <Route path="uncertainty" element={<Uncertainty />} />
          <Route path="events" element={<Events />} />
          <Route path="model" element={<Model />} />
          <Route path="metrics" element={<Metrics />} />
          <Route path="system" element={<System />} />
          <Route path="space" element={<Navigate to="/app/overview" replace />} />
        </Route>
      </Routes>
      </Suspense>
    </BrowserRouter>
  </StrictMode>,
)
