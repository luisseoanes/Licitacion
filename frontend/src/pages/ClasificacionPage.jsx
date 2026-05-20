import { useEffect, useState } from 'react'
import {
  Zap, CheckCircle2, XCircle, AlertTriangle, Brain, Target,
  ChevronRight, BarChart3, Loader2, FileText,
} from 'lucide-react'
import { api } from '../api/client'

const EJEMPLOS = [
  {
    label: 'Servicio cubierto (exacto)',
    glosa: 'Paciente: Ana Torres; DNO: 77889900; SeguroSocial: SS-112233; Edad: 38; PerfilCobertura: PRIORITARIO; ServicioSolicitado: Terapia física ambulatoria; Medicacion: ibuprofeno|paracetamol',
    valor: 85000,
  },
  {
    label: 'Typo en servicio (fuzzy ML)',
    glosa: 'Paciente: Luis Mora; DNO: 55443322; SeguroSocial: SS-998877; Edad: 55; PerfilCobertura: ESTANDAR; ServicioSolicitado: Terapia fisca ambulatoria; Medicacion: aspirina',
    valor: 85000,
  },
  {
    label: 'Servicio no cubierto',
    glosa: 'Paciente: Carlos Ríos; DNO: 11223344; SeguroSocial: SS-556677; Edad: 29; PerfilCobertura: PRIORITARIO; ServicioSolicitado: Cirugía estética; Medicacion: ninguna',
    valor: 4500000,
  },
  {
    label: 'Perfil COPAGO',
    glosa: 'Paciente: María Gómez; DNO: 66554433; SeguroSocial: SS-334455; Edad: 67; PerfilCobertura: COPAGO; ServicioSolicitado: Consulta médica general; Medicacion: metformina|enalapril',
    valor: 120000,
  },
]

function ConfianzaBar({ valor, metodo }) {
  const pct = Math.round(valor * 100)
  const color =
    metodo === 'exacto'
      ? 'bg-emerald-500'
      : metodo === 'fuzzy_ml'
      ? pct >= 85
        ? 'bg-blue-500'
        : 'bg-amber-500'
      : 'bg-gray-400'

  const label =
    metodo === 'exacto'
      ? 'Coincidencia exacta'
      : metodo === 'fuzzy_ml'
      ? 'Coincidencia ML (fuzzy)'
      : metodo === 'sin_match'
      ? 'Sin coincidencia'
      : 'Sin extracción'

  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs text-gray-500">{label}</span>
        <span className="text-sm font-bold text-gray-800">{pct}%</span>
      </div>
      <div className="w-full bg-gray-100 rounded-full h-2.5">
        <div
          className={`${color} h-2.5 rounded-full transition-all duration-700`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

function MetodoBadge({ metodo }) {
  const cfg = {
    exacto:        { cls: 'bg-emerald-50 text-emerald-700 border-emerald-200', label: 'Coincidencia exacta' },
    fuzzy_ml:      { cls: 'bg-blue-50 text-blue-700 border-blue-200',         label: 'ML Fuzzy Match' },
    sin_match:     { cls: 'bg-gray-100 text-gray-600 border-gray-200',        label: 'Sin match' },
    sin_extraccion:{ cls: 'bg-amber-50 text-amber-700 border-amber-200',      label: 'Sin extracción' },
  }[metodo] ?? { cls: 'bg-gray-100 text-gray-600 border-gray-200', label: metodo }

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${cfg.cls}`}>
      {metodo === 'fuzzy_ml' && <Brain className="w-3 h-3" />}
      {metodo === 'exacto' && <Target className="w-3 h-3" />}
      {cfg.label}
    </span>
  )
}

function fmtCurrency(v) {
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(v)
}

function QualityPanel({ quality }) {
  if (!quality) return null
  const { parseo, clasificacion, confianza } = quality
  return (
    <div className="card p-5 space-y-4">
      <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
        <BarChart3 className="w-4 h-4 text-blue-500" />
        Calidad del dataset procesado
      </h3>
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
          <p className="text-xs text-gray-500">Tasa de parseo</p>
          <p className="text-xl font-bold text-gray-900">{parseo.tasa_parseo}%</p>
          <p className="text-xs text-gray-400">{parseo.exitoso.toLocaleString('es-CO')} / {quality.total_registros.toLocaleString('es-CO')}</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
          <p className="text-xs text-gray-500">Confianza media</p>
          <p className="text-xl font-bold text-gray-900">{(confianza.media * 100).toFixed(1)}%</p>
          <p className="text-xs text-gray-400">{confianza.alta_confianza_pct}% alta · {confianza.baja_confianza_pct}% baja</p>
        </div>
      </div>
      <div className="space-y-1.5">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Distribución de métodos</p>
        {[
          { key: 'exacto',        label: 'Exacto',          color: 'bg-emerald-400' },
          { key: 'fuzzy_ml',      label: 'ML Fuzzy',        color: 'bg-blue-400' },
          { key: 'sin_match',     label: 'Sin match',       color: 'bg-gray-400' },
          { key: 'sin_extraccion',label: 'Sin extracción',  color: 'bg-amber-400' },
        ].map(({ key, label, color }) => {
          const count = clasificacion[key] || 0
          const pct = quality.total_registros ? ((count / quality.total_registros) * 100).toFixed(1) : 0
          return (
            <div key={key} className="flex items-center gap-2 text-xs">
              <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${color}`} />
              <span className="text-gray-600 w-28">{label}</span>
              <div className="flex-1 bg-gray-100 rounded-full h-1.5">
                <div className={`${color} h-1.5 rounded-full`} style={{ width: `${pct}%` }} />
              </div>
              <span className="text-gray-500 w-10 text-right">{pct}%</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function ClasificacionPage() {
  const [glosa, setGlosa] = useState('')
  const [valor, setValor] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [quality, setQuality] = useState(null)

  useEffect(() => {
    api.getQuality()
      .then((r) => r.data && setQuality(r.data))
      .catch(() => {})
  }, [])

  async function handleClasificar(e) {
    e?.preventDefault()
    if (!glosa.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await api.classifySingle(glosa, parseFloat(valor) || 0)
      setResult(res)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function cargarEjemplo(ej) {
    setGlosa(ej.glosa)
    setValor(String(ej.valor))
    setResult(null)
    setError(null)
  }

  return (
    <div className="p-6 space-y-6 max-w-screen-xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          <Zap className="w-5 h-5 text-blue-600" />
          Clasificación en Tiempo Real
        </h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Motor híbrido: reglas + ML (TF-IDF fuzzy matching) · Respuesta &lt; 100ms
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Panel izquierdo: Formulario */}
        <div className="lg:col-span-3 space-y-4">
          {/* Ejemplos */}
          <div className="card p-4">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
              Ejemplos de prueba
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {EJEMPLOS.map((ej) => (
                <button
                  key={ej.label}
                  onClick={() => cargarEjemplo(ej)}
                  className="flex items-center gap-2 text-left px-3 py-2 rounded-lg border border-gray-200 hover:border-blue-400 hover:bg-blue-50 transition-colors text-sm text-gray-700"
                >
                  <ChevronRight className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                  {ej.label}
                </button>
              ))}
            </div>
          </div>

          {/* Form */}
          <form onSubmit={handleClasificar} className="card p-5 space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1.5">
                Glosa médica
              </label>
              <textarea
                value={glosa}
                onChange={(e) => setGlosa(e.target.value)}
                rows={6}
                placeholder="Paciente: ...; PerfilCobertura: ESTANDAR; ServicioSolicitado: ..."
                className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1.5">
                Valor del procedimiento (COP)
              </label>
              <input
                type="number"
                value={valor}
                onChange={(e) => setValor(e.target.value)}
                placeholder="Ej: 150000"
                min={0}
                className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <button
              type="submit"
              disabled={loading || !glosa.trim()}
              className="btn-primary w-full justify-center"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
              {loading ? 'Clasificando...' : 'Clasificar ahora'}
            </button>
          </form>

          {/* Error */}
          {error && (
            <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg text-sm">
              <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-red-800">Error al clasificar</p>
                <p className="text-red-600 mt-0.5">{error}</p>
              </div>
            </div>
          )}
        </div>

        {/* Panel derecho: Resultado + Calidad */}
        <div className="lg:col-span-2 space-y-4">
          {/* Resultado */}
          {result ? (
            <div className="card p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-gray-700">Resultado</h3>
                <MetodoBadge metodo={result.metodo} />
              </div>

              {/* Cobertura principal */}
              <div className={`rounded-xl p-4 border ${result.cubre ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'}`}>
                <div className="flex items-center gap-3">
                  {result.cubre
                    ? <CheckCircle2 className="w-8 h-8 text-emerald-600 flex-shrink-0" />
                    : <XCircle className="w-8 h-8 text-red-500 flex-shrink-0" />
                  }
                  <div>
                    <p className={`text-lg font-bold ${result.cubre ? 'text-emerald-800' : 'text-red-800'}`}>
                      {result.cubre ? `Cubierto al ${result.porcentaje_cobertura}%` : 'No cubierto'}
                    </p>
                    <p className={`text-sm ${result.cubre ? 'text-emerald-600' : 'text-red-600'}`}>
                      Perfil: {result.perfil_cobertura}
                    </p>
                  </div>
                </div>
              </div>

              {/* Detalle */}
              <div className="space-y-2 text-sm">
                <div className="flex justify-between py-1.5 border-b border-gray-100">
                  <span className="text-gray-500">Servicio solicitado</span>
                  <span className="font-medium text-gray-800 text-right max-w-[60%] truncate" title={result.servicio_solicitado}>
                    {result.servicio_solicitado || '—'}
                  </span>
                </div>
                {result.metodo === 'fuzzy_ml' && result.servicio_canonico && (
                  <div className="flex justify-between py-1.5 border-b border-gray-100">
                    <span className="text-gray-500 flex items-center gap-1">
                      <Brain className="w-3 h-3" /> Corregido a
                    </span>
                    <span className="font-medium text-blue-700 text-right max-w-[60%] truncate" title={result.servicio_canonico}>
                      {result.servicio_canonico}
                    </span>
                  </div>
                )}
                {result.valor_procedimiento > 0 && (
                  <>
                    <div className="flex justify-between py-1.5 border-b border-gray-100">
                      <span className="text-gray-500">Valor procedimiento</span>
                      <span className="font-mono text-gray-700">{fmtCurrency(result.valor_procedimiento)}</span>
                    </div>
                    <div className="flex justify-between py-1.5">
                      <span className="text-gray-500">Valor cubierto</span>
                      <span className={`font-mono font-bold ${result.cubre ? 'text-emerald-700' : 'text-red-500'}`}>
                        {fmtCurrency(result.valor_cubierto)}
                      </span>
                    </div>
                  </>
                )}
              </div>

              {/* Score de confianza */}
              <div className="pt-2 border-t border-gray-100">
                <p className="text-xs font-semibold text-gray-500 mb-2">Score de confianza del modelo</p>
                <ConfianzaBar valor={result.confianza} metodo={result.metodo} />
              </div>

              {/* Razón de la decisión */}
              {result.razon_decision && (
                <div className="pt-2 border-t border-gray-100">
                  <p className="text-xs font-semibold text-gray-500 mb-1.5 flex items-center gap-1">
                    <FileText className="w-3 h-3" />
                    Fundamento de la decisión
                  </p>
                  <p className="text-xs text-gray-600 leading-relaxed bg-gray-50 rounded-lg p-3 border border-gray-100">
                    {result.razon_decision}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="card flex flex-col items-center justify-center py-14 text-center">
              <Brain className="w-12 h-12 text-gray-200 mb-3" />
              <p className="text-sm font-medium text-gray-500">Motor ML listo</p>
              <p className="text-xs text-gray-400 mt-1 max-w-xs">
                Escribe una glosa o usa un ejemplo para ver la clasificación en tiempo real.
              </p>
            </div>
          )}

          {/* Quality panel */}
          <QualityPanel quality={quality} />
        </div>
      </div>
    </div>
  )
}
