const BASE = (import.meta.env.VITE_API_URL || '') + '/api'
const API_KEY = import.meta.env.VITE_API_KEY || ''

const ERROR_MESSAGES = {
  401: 'Sin autorización. Verifica la API key.',
  403: 'Acceso denegado.',
  404: 'Recurso no encontrado.',
  500: 'Error interno del servidor. Intenta nuevamente.',
  503: 'Servicio no disponible. Verifica que el backend esté activo.',
}

async function request(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers }
  if (API_KEY) headers['X-API-Key'] = API_KEY

  let res
  try {
    res = await fetch(`${BASE}${path}`, { ...options, headers })
  } catch {
    throw new Error('No se pudo conectar con el servidor. Verifica tu conexión.')
  }

  if (!res.ok) {
    const msg = ERROR_MESSAGES[res.status] || `Error del servidor (HTTP ${res.status})`
    throw new Error(msg)
  }

  return res.json()
}

export const api = {
  getStats: () => request('/stats'),

  getProcessStatus: () => request('/process/status'),

  startProcess: () => request('/process', { method: 'POST' }),

  getSolicitudes: (params = {}) => {
    const qs = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v !== null && v !== undefined && v !== '') qs.set(k, v)
    })
    return request(`/solicitudes?${qs.toString()}`)
  },

  exportCsv: () => {
    const url = `${BASE}/export`
    const a = document.createElement('a')
    a.href = API_KEY ? `${url}?` : url
    a.setAttribute('download', 'resultados_clasificacion.csv')
    // Para requests autenticados se necesita fetch + blob
    fetch(url, { headers: API_KEY ? { 'X-API-Key': API_KEY } : {} })
      .then((r) => r.blob())
      .then((blob) => {
        const objUrl = URL.createObjectURL(blob)
        a.href = objUrl
        a.click()
        URL.revokeObjectURL(objUrl)
      })
  },
}
