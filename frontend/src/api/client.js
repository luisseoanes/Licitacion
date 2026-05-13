const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export const api = {
  getStats: () => request('/stats'),

  getProcessStatus: () => request('/process/status'),

  startProcess: () =>
    request('/process', { method: 'POST' }),

  getSolicitudes: (params = {}) => {
    const qs = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v !== null && v !== undefined && v !== '') qs.set(k, v)
    })
    return request(`/solicitudes?${qs.toString()}`)
  },

  exportCsv: () => {
    window.open(`${BASE}/export`, '_blank')
  },
}
