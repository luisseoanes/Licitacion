import { useCallback, useEffect, useState } from 'react'
import { Search, ChevronLeft, ChevronRight, CheckCircle2, XCircle, Filter, Database } from 'lucide-react'
import { api } from '../api/client'

const PERFILES = ['PRIORITARIO', 'ESTANDAR', 'COPAGO']

function fmtCurrency(v) {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0,
  }).format(v)
}

export default function SolicitudesPage() {
  const [data, setData] = useState([])
  const [total, setTotal] = useState(0)
  const [pages, setPages] = useState(1)
  const [loading, setLoading] = useState(true)
  const [noData, setNoData] = useState(false)

  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [perfil, setPerfil] = useState('')
  const [cubre, setCubre] = useState('')
  const [searchInput, setSearchInput] = useState('')

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.getSolicitudes({ page, limit: 50, search, perfil, cubre })
      if (res.error) {
        setNoData(true)
        setData([])
      } else {
        setNoData(false)
        setData(res.data)
        setTotal(res.total)
        setPages(res.pages)
      }
    } catch (_) {
      setNoData(true)
      setData([])
    } finally {
      setLoading(false)
    }
  }, [page, search, perfil, cubre])

  useEffect(() => { fetchData() }, [fetchData])

  // Reset to page 1 on filter change
  useEffect(() => { setPage(1) }, [search, perfil, cubre])

  function handleSearchSubmit(e) {
    e.preventDefault()
    setSearch(searchInput)
  }

  function clearFilters() {
    setSearchInput('')
    setSearch('')
    setPerfil('')
    setCubre('')
  }

  const hasFilters = search || perfil || cubre

  return (
    <div className="p-6 space-y-5 max-w-screen-xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-gray-900">Solicitudes</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Registro trazable de clasificación de órdenes médicas
        </p>
      </div>

      {/* Filters */}
      <div className="card p-4 flex flex-wrap items-center gap-3">
        <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 flex-1 min-w-48">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Buscar ID, servicio, entidad..."
              className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <button type="submit" className="btn-secondary">
            <Filter className="w-4 h-4" /> Filtrar
          </button>
        </form>

        <select
          value={perfil}
          onChange={(e) => setPerfil(e.target.value)}
          className="text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Todos los perfiles</option>
          {PERFILES.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>

        <select
          value={cubre}
          onChange={(e) => setCubre(e.target.value)}
          className="text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Cobertura: Todas</option>
          <option value="true">Cubiertas</option>
          <option value="false">No cubiertas</option>
        </select>

        {hasFilters && (
          <button onClick={clearFilters} className="text-sm text-gray-500 hover:text-gray-700 underline">
            Limpiar filtros
          </button>
        )}

        <span className="ml-auto text-sm text-gray-500 font-medium">
          {total.toLocaleString('es-CO')} resultados
        </span>
      </div>

      {/* No data state */}
      {noData && (
        <div className="card flex flex-col items-center justify-center py-20 text-center">
          <Database className="w-12 h-12 text-gray-300 mb-3" />
          <p className="text-gray-600 font-medium">Sin datos procesados</p>
          <p className="text-sm text-gray-400 mt-1">Ejecuta la clasificación desde el Dashboard primero.</p>
        </div>
      )}

      {/* Table */}
      {!noData && (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="text-left px-4 py-3 font-semibold text-gray-600 whitespace-nowrap">ID Solicitud</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600 whitespace-nowrap">Fecha</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Servicio Solicitado</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600 whitespace-nowrap">Perfil</th>
                  <th className="text-right px-4 py-3 font-semibold text-gray-600 whitespace-nowrap">Valor</th>
                  <th className="text-center px-4 py-3 font-semibold text-gray-600 whitespace-nowrap">Cobertura</th>
                  <th className="text-right px-4 py-3 font-semibold text-gray-600 whitespace-nowrap">Valor Cubierto</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600 whitespace-nowrap">Medio</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {loading
                  ? [...Array(10)].map((_, i) => (
                      <tr key={i} className="animate-pulse">
                        {[...Array(8)].map((_, j) => (
                          <td key={j} className="px-4 py-3">
                            <div className="h-4 bg-gray-100 rounded" />
                          </td>
                        ))}
                      </tr>
                    ))
                  : data.map((row) => (
                      <tr
                        key={row.id_solicitud}
                        className={`hover:bg-gray-50 transition-colors ${
                          row.cubre ? '' : 'bg-red-50/30'
                        }`}
                      >
                        <td className="px-4 py-3 font-mono text-xs text-gray-500 whitespace-nowrap">
                          {row.id_solicitud}
                        </td>
                        <td className="px-4 py-3 text-gray-600 whitespace-nowrap text-xs">
                          {row.fecha_solicitud?.slice(0, 10)}
                        </td>
                        <td className="px-4 py-3 text-gray-700 max-w-xs truncate">
                          {row.servicio_solicitado}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span
                            className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                              row.perfil_cobertura === 'PRIORITARIO'
                                ? 'bg-blue-50 text-blue-700'
                                : row.perfil_cobertura === 'ESTANDAR'
                                ? 'bg-violet-50 text-violet-700'
                                : 'bg-amber-50 text-amber-700'
                            }`}
                          >
                            {row.perfil_cobertura}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right text-gray-700 whitespace-nowrap font-mono text-xs">
                          {fmtCurrency(row.valor_procedimiento)}
                        </td>
                        <td className="px-4 py-3 text-center whitespace-nowrap">
                          {row.cubre ? (
                            <span className="badge-covered">
                              <CheckCircle2 className="w-3 h-3" />
                              {row.porcentaje_cobertura}%
                            </span>
                          ) : (
                            <span className="badge-not-covered">
                              <XCircle className="w-3 h-3" />
                              No cubre
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right whitespace-nowrap font-mono text-xs font-semibold">
                          <span className={row.cubre ? 'text-emerald-700' : 'text-red-500'}>
                            {fmtCurrency(row.valor_cubierto)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap max-w-[120px] truncate">
                          {row.medio_emisor}
                        </td>
                      </tr>
                    ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {!loading && pages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50">
              <p className="text-xs text-gray-500">
                Página {page} de {pages.toLocaleString('es-CO')} ·{' '}
                {total.toLocaleString('es-CO')} registros
              </p>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-1.5 rounded border border-gray-300 disabled:opacity-40 hover:bg-white transition-colors"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                {/* Page numbers */}
                {[...Array(Math.min(5, pages))].map((_, i) => {
                  const p = Math.max(1, Math.min(page - 2, pages - 4)) + i
                  return (
                    <button
                      key={p}
                      onClick={() => setPage(p)}
                      className={`px-2.5 py-1 rounded text-xs border transition-colors ${
                        p === page
                          ? 'bg-blue-600 text-white border-blue-600'
                          : 'border-gray-300 hover:bg-white text-gray-700'
                      }`}
                    >
                      {p}
                    </button>
                  )
                })}
                <button
                  onClick={() => setPage((p) => Math.min(pages, p + 1))}
                  disabled={page === pages}
                  className="p-1.5 rounded border border-gray-300 disabled:opacity-40 hover:bg-white transition-colors"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
