import { useCallback, useEffect, useState } from 'react'
import {
  FileText, CheckCircle2, XCircle, DollarSign, TrendingUp, Database, AlertTriangle,
} from 'lucide-react'
import { api } from '../api/client'
import StatsCard from '../components/StatsCard'
import ProcessPanel from '../components/ProcessPanel'
import {
  CoverageDonut, PerfilBarChart, DailyAreaChart, TopServicesChart, ValorPerfilChart,
} from '../components/Charts'

function fmt(n) {
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(2)}B`
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  return `$${Math.round(n).toLocaleString('es-CO')}`
}

export default function DashboardPage() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchStats = useCallback(async () => {
    setError(null)
    try {
      const res = await api.getStats()
      setStats(res.data)
    } catch (err) {
      setError(err.message)
      setStats(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchStats() }, [fetchStats])

  return (
    <div className="p-6 space-y-6 max-w-screen-xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Dashboard Analítico</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Clasificación de órdenes médicas · Sistema público de salud de Chernovia
          </p>
        </div>
        <ProcessPanel onCompleted={fetchStats} />
      </div>

      {error && (
        <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg text-sm">
          <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-red-800">Error al cargar los datos</p>
            <p className="text-red-600 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {loading && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="card p-5 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-2/3 mb-3" />
              <div className="h-7 bg-gray-200 rounded w-1/2" />
            </div>
          ))}
        </div>
      )}

      {!loading && !stats && (
        <div className="card flex flex-col items-center justify-center py-24 text-center">
          <Database className="w-14 h-14 text-gray-300 mb-4" />
          <h2 className="text-lg font-semibold text-gray-700">Sin datos procesados</h2>
          <p className="text-sm text-gray-400 mt-2 max-w-sm">
            Haz clic en <strong>Iniciar Clasificación</strong> para procesar el dataset de 1.2M solicitudes.
          </p>
        </div>
      )}

      {!loading && stats && (
        <>
          {/* Stat cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatsCard
              title="Total Solicitudes"
              value={stats.total.toLocaleString('es-CO')}
              subtitle="Dataset completo"
              icon={FileText}
              color="blue"
            />
            <StatsCard
              title="Cubiertas"
              value={`${stats.tasa_cobertura}%`}
              subtitle={`${stats.cubiertos.toLocaleString('es-CO')} solicitudes`}
              icon={CheckCircle2}
              color="emerald"
            />
            <StatsCard
              title="No Cubiertas"
              value={`${(100 - stats.tasa_cobertura).toFixed(2)}%`}
              subtitle={`${stats.no_cubiertos.toLocaleString('es-CO')} solicitudes`}
              icon={XCircle}
              color="red"
            />
            <StatsCard
              title="Valor Total Cubierto"
              value={fmt(stats.valor_cubierto_total)}
              subtitle={`de ${fmt(stats.valor_total)} en procedimientos`}
              icon={DollarSign}
              color="violet"
            />
          </div>

          {/* Charts row 1 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <CoverageDonut stats={stats} />
            <PerfilBarChart data={stats.por_perfil} />
          </div>

          {/* Charts row 2 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <DailyAreaChart data={stats.por_dia} />
            <ValorPerfilChart data={stats.por_perfil} />
          </div>

          {/* Top servicios — full width */}
          <TopServicesChart data={stats.por_servicio} />

          {/* Medio emisor table */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">
              Distribución por Medio Emisor
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              {Object.entries(stats.por_medio).map(([medio, count]) => (
                <div key={medio} className="bg-gray-50 rounded-lg p-3 border border-gray-100">
                  <p className="text-xs text-gray-500 truncate">{medio}</p>
                  <p className="text-base font-bold text-gray-900 mt-1">
                    {count.toLocaleString('es-CO')}
                  </p>
                  <p className="text-xs text-gray-400">
                    {((count / stats.total) * 100).toFixed(1)}%
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Footer note */}
          <div className="flex items-center gap-2 text-xs text-gray-400 pb-2">
            <TrendingUp className="w-3.5 h-3.5" />
            <span>
              Arquitectura AWS: S3 → Glue (Spark) → S3 Parquet → Athena · Costo estimado: ~$8/día para 12M solicitudes
            </span>
          </div>
        </>
      )}
    </div>
  )
}
