import { useEffect, useState } from 'react'
import { Play, Loader2, CheckCircle2, AlertCircle, X } from 'lucide-react'
import { api } from '../api/client'

export default function ProcessPanel({ onCompleted }) {
  const [status, setStatus] = useState(null)
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)

  // Poll while processing
  useEffect(() => {
    let interval
    if (status?.estado === 'procesando') {
      interval = setInterval(async () => {
        try {
          const s = await api.getProcessStatus()
          setStatus(s)
          if (s.estado === 'completado') {
            onCompleted?.()
          }
        } catch (_) {}
      }, 1500)
    }
    return () => clearInterval(interval)
  }, [status?.estado, onCompleted])

  // Load current status on mount
  useEffect(() => {
    api.getProcessStatus().then(setStatus).catch(() => {})
  }, [])

  async function handleStart() {
    setLoading(true)
    setOpen(true)
    try {
      await api.startProcess()
      const s = await api.getProcessStatus()
      setStatus(s)
    } catch (e) {
      setStatus({ estado: 'error', error: e.message })
    } finally {
      setLoading(false)
    }
  }

  const isIdle = !status || status.estado === 'idle'
  const isProcessing = status?.estado === 'procesando'
  const isDone = status?.estado === 'completado'
  const isError = status?.estado === 'error'

  return (
    <>
      {/* Trigger button */}
      <button
        onClick={isDone || isError ? () => setOpen(true) : handleStart}
        disabled={isProcessing || loading}
        className="btn-primary"
      >
        {isProcessing || loading ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : isDone ? (
          <CheckCircle2 className="w-4 h-4" />
        ) : (
          <Play className="w-4 h-4" />
        )}
        {isProcessing || loading
          ? 'Procesando...'
          : isDone
          ? 'Reprocesar'
          : 'Iniciar Clasificación'}
      </button>

      {/* Modal */}
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="card w-full max-w-md p-6 mx-4">
            <div className="flex items-center justify-between mb-5">
              <h3 className="font-semibold text-gray-900 text-base">Estado del Procesamiento</h3>
              {!isProcessing && (
                <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-gray-600">
                  <X className="w-5 h-5" />
                </button>
              )}
            </div>

            {/* Processing */}
            {isProcessing && (
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <Loader2 className="w-5 h-5 text-blue-600 animate-spin flex-shrink-0" />
                  <span className="text-sm text-gray-700">{status.paso || 'Procesando...'}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${status.progreso ?? 0}%` }}
                  />
                </div>
                <p className="text-xs text-gray-400 text-right">{status.progreso ?? 0}% completado</p>
              </div>
            )}

            {/* Completed */}
            {isDone && (
              <div className="space-y-4">
                <div className="flex items-center gap-3 p-3 bg-emerald-50 rounded-lg border border-emerald-200">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-emerald-800">¡Clasificación completada!</p>
                    <p className="text-xs text-emerald-600 mt-0.5">
                      {status.total?.toLocaleString('es-CO')} solicitudes procesadas
                    </p>
                  </div>
                </div>
                {status.inicio && status.fin && (
                  <p className="text-xs text-gray-400">
                    Duración:{' '}
                    {Math.round(
                      (new Date(status.fin) - new Date(status.inicio)) / 1000,
                    )}{' '}
                    segundos
                  </p>
                )}
                <div className="flex justify-between gap-3 pt-2">
                  <button onClick={handleStart} className="btn-secondary flex-1">
                    <Play className="w-4 h-4" /> Reprocesar
                  </button>
                  <button onClick={() => setOpen(false)} className="btn-primary flex-1">
                    Ver resultados
                  </button>
                </div>
              </div>
            )}

            {/* Error */}
            {isError && (
              <div className="space-y-4">
                <div className="flex items-start gap-3 p-3 bg-red-50 rounded-lg border border-red-200">
                  <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-red-800">Error en el procesamiento</p>
                    <p className="text-xs text-red-600 mt-0.5">{status.error}</p>
                  </div>
                </div>
                <button onClick={handleStart} className="btn-primary w-full">
                  Reintentar
                </button>
              </div>
            )}

            {/* Idle / not started */}
            {isIdle && !isProcessing && !isDone && !isError && (
              <div className="text-center py-4">
                <p className="text-sm text-gray-500">
                  Haz clic en "Iniciar Clasificación" para procesar el dataset.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  )
}
