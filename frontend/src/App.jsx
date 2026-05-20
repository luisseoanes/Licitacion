import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import DashboardPage from './pages/DashboardPage'
import SolicitudesPage from './pages/SolicitudesPage'
import ClasificacionPage from './pages/ClasificacionPage'
import AnomaliaPage from './pages/AnomaliaPage'
import SimuladorPage from './pages/SimuladorPage'
import CatalogoPage from './pages/CatalogoPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="solicitudes" element={<SolicitudesPage />} />
          <Route path="clasificar" element={<ClasificacionPage />} />
          <Route path="anomalias" element={<AnomaliaPage />} />
          <Route path="simulador" element={<SimuladorPage />} />
          <Route path="catalogo" element={<CatalogoPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
