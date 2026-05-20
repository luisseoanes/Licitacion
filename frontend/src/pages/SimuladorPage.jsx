import { useState } from 'react'
import {
  TrendingUp, Plus, X, Loader2, BarChart3,
  ArrowUp, ArrowDown, Minus, AlertTriangle,
} from 'lucide-react'
import { api } from '../api/client'

const PERFILES_DEFAULT = { PRIORITARIO: 100, ESTANDAR: 50, COPAGO: 25 }

function fmtCOP(v) {
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(v)
}

function DeltaBadge({ value, suffix = '' }) {
  if (value === 0) return <span className="text-gray-400 flex items-center gap-1 text-sm"><Minus className="w-3 h-3" /> Sin cambio</span>
  const pos = value > 0
  return (
    <span className={`flex items-center gap-1 text-sm font-semibold ${pos ? 'text-emerald-600' : 'text-red-600'}`}>
      {pos ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />}
      {pos ? '+' : ''}{typeof value === 'number' && !Number.isInteger(value) ? value.toFixed(2) : value.toLocaleString('es-CO')}{suffix}
    </span>
  )
}

export default function SimuladorPage() {
  const [serviciosAgregar, setServiciosAgregar] = useState([])
  const [serviciosQuitar, setServiciosQuitar] = useState([])
  const [perfiles, setPerfiles] = useState({ ...PERFILES_DEFAULT })
  const [inputAgregar, setInputAgregar] = useState('')
  const [inputQuitar, setInputQuitar] = useState('')
  const [resultado, setResultado] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  function addServicio(lista, setLista, input, setInput) {
    const val = input.trim()
    if (val && !lista.includes(val)) setLista([...lista, val])
    setInput('')
  }

  function removeServicio(lista, setLista, item) {
    setLista(lista.filter((s) => s !== item))
  }

  async function simular() {
    setLoading(true)
    setError(null)
    setResultado(null)
    try {
      const cambiarPerfiles = {}
      Object.entries(perfiles).forEach(([k, v]) => {
        if (v !== PERFILES_DEFAULT[k]) cambiarPerfiles[k] = Number(v)
      })
      const res = await api.simulate({
        agregar_servicios: serviciosAgregar,
        quitar_servicios: serviciosQuitar,
        cambiar_perfiles: cambiarPerfiles,
      })
      setResultado(res)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const hayCambios =
    serviciosAgregar.length > 0 ||
    serviciosQuitar.length > 0 ||
    Object.entries(perfiles).some(([k, v]) => Number(v) !== PERFILES_DEFAULT[k])

  return (
    <div className="p-6 space-y-6 max-w-screen-xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-blue-600" />
          Simulador de Política de Cobertura
        </h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Proyecta el impacto fiscal antes de modificar el catálogo de servicios o los porcentajes de cobertura
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Panel izquierdo: configuración */}
        <div className="space-y-5">
          {/* Agregar servicios */}
          <div className="card p-5 space-y-3">
            <h2 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
              <Plus className="w-4 h-4 text-emerald-600" />
              Agregar servicios al catálogo cubierto
            </h2>
            <div className="flex gap-2">
              <input
                value={inputAgregar}
                onChange={(e) => setInputAgregar(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addServicio(serviciosAgregar, setServiciosAgregar, inputAgregar, setInputAgregar)}
                placeholder="Ej: Fisioterapia domiciliaria"
                className="flex-1 text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={() => addServicio(serviciosAgregar, setServiciosAgregar, inputAgregar, setInputAgregar)}
                className="px-3 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {serviciosAgregar.map((s) => (
                <span key={s} className="flex items-center gap-1 px-2.5 py-1 bg-emerald-50 border border-emerald-200 rounded-full text-xs text-emerald-800">
                  {s}
                  <button onClick={() => removeServicio(serviciosAgregar, setServiciosAgregar, s)}>
                    <X className="w-3 h-3 hover:text-red-500" />
                  </button>
                </span>
              ))}
              {serviciosAgregar.length === 0 && (
                <p className="text-xs text-gray-400">Ningún servicio para agregar</p>
              )}
            </div>
          </div>

          {/* Quitar servicios */}
          <div className="card p-5 space-y-3">
            <h2 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
              <X className="w-4 h-4 text-red-500" />
              Quitar servicios del catálogo cubierto
            </h2>
            <div className="flex gap-2">
              <input
                value={inputQuitar}
                onChange={(e) => setInputQuitar(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addServicio(serviciosQuitar, setServiciosQuitar, inputQuitar, setInputQuitar)}
                placeholder="Ej: Cirugía estética"
                className="flex-1 text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={() => addServicio(serviciosQuitar, setServiciosQuitar, inputQuitar, setInputQuitar)}
                className="px-3 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {serviciosQuitar.map((s) => (
                <span key={s} className="flex items-center gap-1 px-2.5 py-1 bg-red-50 border border-red-200 rounded-full text-xs text-red-800">
                  {s}
                  <button onClick={() => removeServicio(serviciosQuitar, setServiciosQuitar, s)}>
                    <X className="w-3 h-3 hover:text-red-700" />
                  </button>
                </span>
              ))}
              {serviciosQuitar.length === 0 && (
                <p className="text-xs text-gray-400">Ningún servicio para quitar</p>
              )}
            </div>
          </div>

          {/* Cambiar porcentajes de perfiles */}
          <div className="card p-5 space-y-4">
            <h2 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-blue-500" />
              Ajustar porcentajes de cobertura por perfil
            </h2>
            {Object.entries(perfiles).map(([perfil, pct]) => (
              <div key={perfil} className="space-y-1">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-gray-700">{perfil}</label>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-blue-700">{pct}%</span>
                    {Number(pct) !== PERFILES_DEFAULT[perfil] && (
                      <span className="text-xs text-amber-600 font-semibold">
                        (era {PERFILES_DEFAULT[perfil]}%)
                      </span>
                    )}
                  </div>
                </div>
                <input
                  type="range"
                  min={0}
                  max={100}
                  step={5}
                  value={pct}
                  onChange={(e) => setPerfiles({ ...perfiles, [perfil]: Number(e.target.value) })}
                  className="w-full accent-blue-600"
                />
                <div className="flex justify-between text-xs text-gray-400">
                  <span>0%</span><span>50%</span><span>100%</span>
                </div>
              </div>
            ))}
          </div>

          {/* Botón simular */}
          <button
            onClick={simular}
            disabled={loading || !hayCambios}
            className="btn-primary w-full justify-center"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <TrendingUp className="w-4 h-4" />}
            {loading ? 'Calculando impacto...' : 'Proyectar impacto fiscal'}
          </button>

          {!hayCambios && (
            <p className="text-xs text-center text-gray-400">
              Configura al menos un cambio para habilitar la simulación
            </p>
          )}
        </div>

        {/* Panel derecho: resultado */}
        <div className="space-y-4">
          {error && (
            <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg text-sm">
              <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <p className="text-red-700">{error}</p>
            </div>
          )}

          {resultado ? (
            <>
              {/* Estado actual vs proyectado */}
              <div className="grid grid-cols-2 gap-4">
                <div className="card p-4 border-l-4 border-l-gray-300">
                  <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Estado actual</p>
                  <div className="space-y-1.5 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Total solicitudes</span>
                      <span className="font-medium">{resultado.estado_actual.total_solicitudes.toLocaleString('es-CO')}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Cubiertas</span>
                      <span className="font-medium">{resultado.estado_actual.cubiertos.toLocaleString('es-CO')}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Tasa cobertura</span>
                      <span className="font-bold text-blue-700">{resultado.estado_actual.tasa_cobertura_pct}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Valor cubierto</span>
                      <span className="font-medium text-xs">{fmtCOP(resultado.estado_actual.valor_cubierto_total)}</span>
                    </div>
                  </div>
                </div>

                <div className="card p-4 border-l-4 border-l-blue-500">
                  <p className="text-xs font-semibold text-blue-500 uppercase tracking-wide mb-2">Con los cambios</p>
                  <div className="space-y-1.5 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Nuevas cubiertas</span>
                      <DeltaBadge value={resultado.impacto_proyectado.nuevos_cubiertos} />
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Total cubiertos</span>
                      <span className="font-medium">{resultado.impacto_proyectado.total_cubiertos_nuevo.toLocaleString('es-CO')}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Nueva tasa</span>
                      <span className="font-bold text-blue-700">{resultado.impacto_proyectado.nueva_tasa_cobertura_pct}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Var. tasa</span>
                      <DeltaBadge value={resultado.impacto_proyectado.variacion_tasa_pct} suffix="%" />
                    </div>
                  </div>
                </div>
              </div>

              {/* Impacto fiscal destacado */}
              <div className={`card p-5 border-2 ${resultado.impacto_proyectado.delta_valor_cubierto >= 0 ? 'border-amber-300 bg-amber-50' : 'border-emerald-300 bg-emerald-50'}`}>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Impacto fiscal total</p>
                <p className={`text-3xl font-bold ${resultado.impacto_proyectado.delta_valor_cubierto >= 0 ? 'text-amber-700' : 'text-emerald-700'}`}>
                  {resultado.impacto_proyectado.delta_valor_cubierto >= 0 ? '+' : ''}
                  {fmtCOP(resultado.impacto_proyectado.delta_valor_cubierto)}
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  Nuevo valor cubierto total: {fmtCOP(resultado.impacto_proyectado.nuevo_valor_cubierto_total)}
                </p>
              </div>

              {/* Detalle de cambios */}
              {resultado.detalle_cambios?.length > 0 && (
                <div className="card p-4 space-y-2">
                  <h3 className="text-sm font-semibold text-gray-700">Detalle por cambio</h3>
                  {resultado.detalle_cambios.map((d, i) => (
                    <div key={i} className="flex items-start justify-between gap-3 py-2 border-b border-gray-100 last:border-0 text-sm">
                      <span className="text-gray-700 flex-1">{d.cambio}</span>
                      <div className="text-right flex-shrink-0">
                        {d.solicitudes_nuevas_cubiertas != null && (
                          <p className="text-xs text-gray-500">{d.solicitudes_nuevas_cubiertas.toLocaleString('es-CO')} solicitudes</p>
                        )}
                        {d.solicitudes_afectadas != null && (
                          <p className="text-xs text-gray-500">{d.solicitudes_afectadas.toLocaleString('es-CO')} solicitudes</p>
                        )}
                        {d.costo_adicional != null && (
                          <p className="text-xs font-semibold text-amber-600">+{fmtCOP(d.costo_adicional)}</p>
                        )}
                        {d.ahorro != null && (
                          <p className="text-xs font-semibold text-emerald-600">-{fmtCOP(d.ahorro)}</p>
                        )}
                        {d.variacion_valor != null && (
                          <p className={`text-xs font-semibold ${d.variacion_valor >= 0 ? 'text-amber-600' : 'text-emerald-600'}`}>
                            {d.variacion_valor >= 0 ? '+' : ''}{fmtCOP(d.variacion_valor)}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div className="card flex flex-col items-center py-20 text-center">
              <TrendingUp className="w-12 h-12 text-gray-200 mb-3" />
              <p className="text-sm font-medium text-gray-500">El resultado aparecerá aquí</p>
              <p className="text-xs text-gray-400 mt-1 max-w-xs">
                Configura cambios a la izquierda y presiona "Proyectar impacto fiscal" para ver la simulación.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
