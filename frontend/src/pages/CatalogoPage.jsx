import { useEffect, useState } from 'react'
import {
  BookOpen, Plus, Trash2, RefreshCw, Loader2,
  CheckCircle2, XCircle, AlertTriangle, Save, Edit2,
} from 'lucide-react'
import { api } from '../api/client'

function EstadoBadge({ cubre }) {
  return cubre === 'SI'
    ? <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200"><CheckCircle2 className="w-3 h-3" /> Cubierto</span>
    : <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-red-50 text-red-700 border border-red-200"><XCircle className="w-3 h-3" /> No cubierto</span>
}

export default function CatalogoPage() {
  const [servicios, setServicios] = useState([])
  const [perfiles, setPerfiles] = useState([])
  const [loadingSvc, setLoadingSvc] = useState(false)
  const [loadingPrf, setLoadingPrf] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  // Nuevo servicio
  const [nuevoServicio, setNuevoServicio] = useState('')
  const [nuevoCubre, setNuevoCubre] = useState('SI')
  const [addingService, setAddingService] = useState(false)

  // Editar perfil
  const [editPerfilId, setEditPerfilId] = useState(null)
  const [editPerfilPct, setEditPerfilPct] = useState(0)
  const [savingPerfil, setSavingPerfil] = useState(false)

  // Búsqueda
  const [busqueda, setBusqueda] = useState('')
  const [filtroEstado, setFiltroEstado] = useState('TODOS')

  function mostrarMensaje(msg, esError = false) {
    if (esError) { setError(msg); setSuccess(null) }
    else { setSuccess(msg); setError(null) }
    setTimeout(() => { setError(null); setSuccess(null) }, 4000)
  }

  async function cargarServicios() {
    setLoadingSvc(true)
    try {
      const res = await api.getCatalogoServicios()
      setServicios(res.data || [])
    } catch (err) {
      mostrarMensaje(err.message, true)
    } finally {
      setLoadingSvc(false)
    }
  }

  async function cargarPerfiles() {
    setLoadingPrf(true)
    try {
      const res = await api.getCatalogoPerfiles()
      setPerfiles(res.data || [])
    } catch (err) {
      mostrarMensaje(err.message, true)
    } finally {
      setLoadingPrf(false)
    }
  }

  useEffect(() => {
    cargarServicios()
    cargarPerfiles()
  }, [])

  async function handleAddServicio(e) {
    e.preventDefault()
    const nombre = nuevoServicio.trim()
    if (!nombre) return
    setAddingService(true)
    try {
      const res = await api.addServicio(nombre, nuevoCubre)
      mostrarMensaje(res.message)
      setNuevoServicio('')
      await cargarServicios()
    } catch (err) {
      mostrarMensaje(err.message, true)
    } finally {
      setAddingService(false)
    }
  }

  async function handleDeleteServicio(nombre) {
    if (!confirm(`¿Eliminar el servicio "${nombre}" del catálogo?`)) return
    try {
      const res = await api.deleteServicio(nombre)
      mostrarMensaje(res.message)
      await cargarServicios()
    } catch (err) {
      mostrarMensaje(err.message, true)
    }
  }

  async function handleSavePerfil(perfil) {
    setSavingPerfil(true)
    try {
      const res = await api.updatePerfil(perfil, editPerfilPct)
      mostrarMensaje(res.message)
      setEditPerfilId(null)
      await cargarPerfiles()
    } catch (err) {
      mostrarMensaje(err.message, true)
    } finally {
      setSavingPerfil(false)
    }
  }

  const serviciosFiltrados = servicios.filter((s) => {
    const matchBusqueda = s.servicio?.toLowerCase().includes(busqueda.toLowerCase())
    const matchEstado = filtroEstado === 'TODOS' || s.cubre_sistema_publico === filtroEstado
    return matchBusqueda && matchEstado
  })

  const totalCubiertos = servicios.filter((s) => s.cubre_sistema_publico === 'SI').length
  const totalNoCubiertos = servicios.filter((s) => s.cubre_sistema_publico === 'NO').length

  return (
    <div className="p-6 space-y-6 max-w-screen-xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-blue-600" />
          Administración de Catálogos
        </h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Gestiona los servicios cubiertos y porcentajes de cobertura sin necesidad de código
        </p>
      </div>

      {/* Alertas */}
      {error && (
        <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg text-sm">
          <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <p className="text-red-700">{error}</p>
        </div>
      )}
      {success && (
        <div className="flex items-start gap-3 p-4 bg-emerald-50 border border-emerald-200 rounded-lg text-sm">
          <CheckCircle2 className="w-5 h-5 text-emerald-500 flex-shrink-0 mt-0.5" />
          <p className="text-emerald-700">{success}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Columna izquierda: perfiles */}
        <div className="space-y-4">
          <div className="card p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-gray-700">Perfiles de cobertura</h2>
              <button onClick={cargarPerfiles} disabled={loadingPrf} className="text-gray-400 hover:text-gray-600">
                <RefreshCw className={`w-4 h-4 ${loadingPrf ? 'animate-spin' : ''}`} />
              </button>
            </div>
            <p className="text-xs text-gray-400">Porcentaje reconocido cuando el servicio sí está cubierto</p>

            {perfiles.map((p) => {
              const colName = 'porcentaje_cobertura_si_el_servicio_esta_cubierto'
              const pct = p[colName]
              const isEditing = editPerfilId === p.perfil_cobertura
              return (
                <div key={p.perfil_cobertura} className="rounded-lg border border-gray-200 p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-gray-800">{p.perfil_cobertura}</span>
                    {!isEditing ? (
                      <button
                        onClick={() => { setEditPerfilId(p.perfil_cobertura); setEditPerfilPct(pct) }}
                        className="text-gray-400 hover:text-blue-600 transition-colors"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                    ) : (
                      <button
                        onClick={() => setEditPerfilId(null)}
                        className="text-gray-400 hover:text-red-500 text-xs"
                      >Cancelar</button>
                    )}
                  </div>

                  {!isEditing ? (
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-gray-500">Cobertura</span>
                        <span className="font-bold text-blue-700">{pct}%</span>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-2">
                        <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-gray-500">Nuevo porcentaje</span>
                        <span className="text-sm font-bold text-blue-700">{editPerfilPct}%</span>
                      </div>
                      <input
                        type="range" min={0} max={100} step={5}
                        value={editPerfilPct}
                        onChange={(e) => setEditPerfilPct(Number(e.target.value))}
                        className="w-full accent-blue-600"
                      />
                      <button
                        onClick={() => handleSavePerfil(p.perfil_cobertura)}
                        disabled={savingPerfil}
                        className="w-full flex items-center justify-center gap-2 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 transition-colors"
                      >
                        {savingPerfil ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                        Guardar
                      </button>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Columna derecha: servicios */}
        <div className="lg:col-span-2 space-y-4">
          {/* Agregar servicio */}
          <div className="card p-5">
            <h2 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <Plus className="w-4 h-4 text-emerald-600" />
              Agregar / actualizar servicio
            </h2>
            <form onSubmit={handleAddServicio} className="flex flex-col sm:flex-row gap-3">
              <input
                value={nuevoServicio}
                onChange={(e) => setNuevoServicio(e.target.value)}
                placeholder="Nombre del servicio médico"
                className="flex-1 text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <select
                value={nuevoCubre}
                onChange={(e) => setNuevoCubre(e.target.value)}
                className="text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="SI">Cubierto (SI)</option>
                <option value="NO">No cubierto (NO)</option>
              </select>
              <button
                type="submit"
                disabled={addingService || !nuevoServicio.trim()}
                className="btn-primary flex items-center gap-2 whitespace-nowrap"
              >
                {addingService ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                Agregar
              </button>
            </form>
          </div>

          {/* KPIs */}
          <div className="grid grid-cols-3 gap-3">
            <div className="card p-3 text-center">
              <p className="text-xs text-gray-500">Total servicios</p>
              <p className="text-xl font-bold text-gray-900">{servicios.length}</p>
            </div>
            <div className="card p-3 text-center">
              <p className="text-xs text-gray-500">Cubiertos</p>
              <p className="text-xl font-bold text-emerald-700">{totalCubiertos}</p>
            </div>
            <div className="card p-3 text-center">
              <p className="text-xs text-gray-500">No cubiertos</p>
              <p className="text-xl font-bold text-red-600">{totalNoCubiertos}</p>
            </div>
          </div>

          {/* Filtros */}
          <div className="flex flex-wrap gap-3 items-center">
            <input
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              placeholder="Buscar servicio..."
              className="flex-1 min-w-40 text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <select
              value={filtroEstado}
              onChange={(e) => setFiltroEstado(e.target.value)}
              className="text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="TODOS">Todos</option>
              <option value="SI">Solo cubiertos</option>
              <option value="NO">Solo no cubiertos</option>
            </select>
            <button onClick={cargarServicios} disabled={loadingSvc} className="text-gray-400 hover:text-gray-700 transition-colors">
              <RefreshCw className={`w-4 h-4 ${loadingSvc ? 'animate-spin' : ''}`} />
            </button>
            <span className="text-xs text-gray-400">{serviciosFiltrados.length} servicios</span>
          </div>

          {/* Tabla de servicios */}
          <div className="card overflow-hidden">
            <div className="overflow-x-auto max-h-[420px] overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200 sticky top-0">
                  <tr>
                    <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">Servicio</th>
                    <th className="text-center px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">Estado</th>
                    <th className="text-center px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {loadingSvc ? (
                    <tr><td colSpan={3} className="text-center py-8 text-gray-400">
                      <Loader2 className="w-5 h-5 animate-spin mx-auto" />
                    </td></tr>
                  ) : serviciosFiltrados.length === 0 ? (
                    <tr><td colSpan={3} className="text-center py-8 text-gray-400 text-sm">
                      Sin resultados para la búsqueda
                    </td></tr>
                  ) : (
                    serviciosFiltrados.map((s, i) => (
                      <tr key={i} className="hover:bg-gray-50 transition-colors">
                        <td className="px-4 py-2.5 text-gray-800">{s.servicio}</td>
                        <td className="px-4 py-2.5 text-center">
                          <EstadoBadge cubre={s.cubre_sistema_publico} />
                        </td>
                        <td className="px-4 py-2.5 text-center">
                          <div className="flex items-center justify-center gap-2">
                            <button
                              onClick={() => { api.addServicio(s.servicio, s.cubre_sistema_publico === 'SI' ? 'NO' : 'SI').then(() => { mostrarMensaje(`${s.servicio} actualizado.`); cargarServicios() }).catch((e) => mostrarMensaje(e.message, true)) }}
                              className="text-xs px-2 py-1 rounded border border-gray-300 hover:border-blue-400 hover:text-blue-600 transition-colors"
                            >
                              Cambiar estado
                            </button>
                            <button
                              onClick={() => handleDeleteServicio(s.servicio)}
                              className="text-gray-400 hover:text-red-500 transition-colors p-1"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
