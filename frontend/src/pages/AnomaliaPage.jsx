import { useEffect, useState } from 'react'
import {
  AlertTriangle, ShieldAlert, RefreshCw, Loader2,
  AlertCircle, CheckCircle2, Info,
} from 'lucide-react'
import { api } from '../api/client'

const GRAVEDAD_CFG = {
  ALTA:  { cls: 'bg-red-50 border-red-300 text-red-800',    badge: 'bg-red-100 text-red-700',    icon: AlertCircle },
  MEDIA: { cls: 'bg-amber-50 border-amber-300 text-amber-800', badge: 'bg-amber-100 text-amber-700', icon: AlertTriangle },
  BAJA:  { cls: 'bg-blue-50 border-blue-300 text-blue-800',  badge: 'bg-blue-100 text-blue-700',  icon: Info },
}

const TIPO_LABEL = {
  DUPLICADO:             'Solicitud duplicada',
  VALOR_ATIPICO:         'Valor atípico (>3σ)',
  ENTIDAD_SOSPECHOSA:    'Entidad sospechosa',
  INCOMPATIBILIDAD_EDAD: 'Incompatibilidad edad-servicio',
}

function GravedadBadge({ gravedad }) {
  const cfg = GRAVEDAD_CFG[gravedad] || GRAVEDAD_CFG.BAJA
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${cfg.badge}`}>
      {gravedad}
    </span>
  )
}

function ResumenCard({ item }) {
  const cfg = GRAVEDAD_CFG[item.gravedad] || GRAVEDAD_CFG.BAJA
  const Icon = cfg.icon
  return (
    <div className={`rounded-xl border p-4 flex items-start gap-3 ${cfg.cls}`}>
      <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm font-semibold">{TIPO_LABEL[item.tipo] || item.tipo.replace(/_/g, ' ')}</p>
          <GravedadBadge gravedad={item.gravedad} />
        </div>
        <p className="text-xs mt-0.5 opacity-70">{item.codigo}</p>
        <p className="text-lg font-bold mt-1">{item.total.toLocaleString('es-CO')} casos</p>
      </div>
    </div>
  )
}

export default function AnomaliaPage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [filtroTipo, setFiltroTipo] = useState('TODOS')
  const [filtroGravedad, setFiltroGravedad] = useState('TODOS')

  async function cargar() {
    setLoading(true)
    setError(null)
    try {
      const res = await api.getAnomalias()
      setData(res.data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { cargar() }, [])

  const anomalias = data?.anomalias || []
  const resumen = data?.resumen_por_tipo || []
  const tipos = ['TODOS', ...new Set(anomalias.map((a) => a.tipo))]

  const filtradas = anomalias.filter((a) => {
    if (filtroTipo !== 'TODOS' && a.tipo !== filtroTipo) return false
    if (filtroGravedad !== 'TODOS' && a.gravedad !== filtroGravedad) return false
    return true
  })

  return (
    <div className="p-6 space-y-6 max-w-screen-xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-red-600" />
            Detección de Anomalías y Fraude
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Análisis automático de patrones sospechosos en las solicitudes procesadas
          </p>
        </div>
        <button
          onClick={cargar}
          disabled={loading}
          className="btn-primary flex items-center gap-2"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          Analizar
        </button>
      </div>

      {error && (
        <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg text-sm">
          <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <p className="text-red-700">{error}</p>
        </div>
      )}

      {data && (
        <>
          {/* KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              {
                label: 'Solicitudes analizadas',
                valor: data.total_solicitudes_analizadas?.toLocaleString('es-CO') ?? '—',
                cls: 'text-gray-900',
              },
              {
                label: 'Anomalías detectadas',
                valor: data.total_anomalias?.toLocaleString('es-CO') ?? '0',
                cls: 'text-red-700',
              },
              {
                label: 'Tasa de anomalía',
                valor: `${data.tasa_anomalia_pct ?? 0}%`,
                cls: 'text-amber-700',
              },
              {
                label: 'Estado del sistema',
                valor: data.total_anomalias === 0 ? 'Limpio' : 'Alertas activas',
                cls: data.total_anomalias === 0 ? 'text-emerald-700' : 'text-red-700',
                icon: data.total_anomalias === 0 ? CheckCircle2 : AlertCircle,
              },
            ].map(({ label, valor, cls, icon: Icon }) => (
              <div key={label} className="card p-4">
                <p className="text-xs text-gray-500 mb-1">{label}</p>
                <div className="flex items-center gap-2">
                  {Icon && <Icon className={`w-4 h-4 ${cls}`} />}
                  <p className={`text-xl font-bold ${cls}`}>{valor}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Resumen por tipo */}
          {resumen.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-gray-700 mb-3">Resumen por tipo de anomalía</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {resumen.map((item) => <ResumenCard key={item.tipo} item={item} />)}
              </div>
            </div>
          )}

          {/* Filtros */}
          <div className="flex flex-wrap gap-3 items-center">
            <div>
              <label className="text-xs font-semibold text-gray-500 mr-2">Tipo:</label>
              <select
                value={filtroTipo}
                onChange={(e) => setFiltroTipo(e.target.value)}
                className="text-sm border border-gray-300 rounded-lg px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {tipos.map((t) => (
                  <option key={t} value={t}>{t === 'TODOS' ? 'Todos los tipos' : (TIPO_LABEL[t] || t)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold text-gray-500 mr-2">Gravedad:</label>
              <select
                value={filtroGravedad}
                onChange={(e) => setFiltroGravedad(e.target.value)}
                className="text-sm border border-gray-300 rounded-lg px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {['TODOS', 'ALTA', 'MEDIA', 'BAJA'].map((g) => (
                  <option key={g} value={g}>{g === 'TODOS' ? 'Todas las gravedades' : g}</option>
                ))}
              </select>
            </div>
            <span className="text-xs text-gray-400">{filtradas.length} registros</span>
          </div>

          {/* Lista de anomalías */}
          <div className="space-y-2">
            {filtradas.length === 0 ? (
              <div className="card flex flex-col items-center py-12 text-center">
                <CheckCircle2 className="w-10 h-10 text-emerald-400 mb-2" />
                <p className="text-sm font-medium text-gray-600">Sin anomalías para los filtros seleccionados</p>
              </div>
            ) : (
              filtradas.map((a, i) => {
                const cfg = GRAVEDAD_CFG[a.gravedad] || GRAVEDAD_CFG.BAJA
                const Icon = cfg.icon
                return (
                  <div key={i} className={`rounded-xl border p-4 flex items-start gap-3 ${cfg.cls}`}>
                    <Icon className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-mono opacity-60">{a.codigo}</span>
                        <GravedadBadge gravedad={a.gravedad} />
                        <span className="text-xs font-semibold">
                          {TIPO_LABEL[a.tipo] || a.tipo.replace(/_/g, ' ')}
                        </span>
                      </div>
                      <p className="text-sm mt-1">{a.descripcion}</p>
                      {a.ids_afectados?.length > 0 && (
                        <p className="text-xs opacity-60 mt-1">
                          IDs: {a.ids_afectados.join(', ')}
                        </p>
                      )}
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </>
      )}

      {!data && !loading && !error && (
        <div className="card flex flex-col items-center py-16 text-center">
          <ShieldAlert className="w-12 h-12 text-gray-200 mb-3" />
          <p className="text-sm font-medium text-gray-500">Haz clic en Analizar para detectar anomalías</p>
        </div>
      )}
    </div>
  )
}
