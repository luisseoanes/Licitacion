import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  AreaChart, Area,
} from 'recharts'

const COLORS = {
  covered: '#10b981',
  notCovered: '#ef4444',
  prioritario: '#3b82f6',
  estandar: '#8b5cf6',
  copago: '#f59e0b',
}

const PERFIL_COLORS = { PRIORITARIO: '#3b82f6', ESTANDAR: '#8b5cf6', COPAGO: '#f59e0b' }

function fmt(n) {
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(1)}B`
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`
  return `$${n}`
}

// ── Donut: cubiertos vs no cubiertos ────────────────────────────────────────
export function CoverageDonut({ stats }) {
  const data = [
    { name: 'Cubiertos', value: stats.cubiertos },
    { name: 'No Cubiertos', value: stats.no_cubiertos },
  ]

  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">Cobertura General</h3>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={90}
            paddingAngle={3}
            dataKey="value"
          >
            <Cell fill={COLORS.covered} />
            <Cell fill={COLORS.notCovered} />
          </Pie>
          <Tooltip formatter={(v) => v.toLocaleString('es-CO')} />
          <Legend
            formatter={(value, entry) => (
              <span className="text-xs text-gray-600">
                {value} ({((entry.payload.value / stats.total) * 100).toFixed(1)}%)
              </span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── Bar: por perfil ──────────────────────────────────────────────────────────
export function PerfilBarChart({ data }) {
  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">Solicitudes por Perfil</h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
          <XAxis dataKey="perfil_cobertura" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => (v / 1000).toFixed(0) + 'K'} />
          <Tooltip
            formatter={(v, name) => [v.toLocaleString('es-CO'), name]}
            labelStyle={{ fontWeight: 600 }}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar dataKey="total" name="Total" fill="#94a3b8" radius={[4, 4, 0, 0]} />
          <Bar dataKey="cubiertos" name="Cubiertos" fill={COLORS.covered} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── Area: por día ────────────────────────────────────────────────────────────
export function DailyAreaChart({ data }) {
  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">Volumen Diario de Solicitudes</h3>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="gTotal" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="gCubiertos" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={COLORS.covered} stopOpacity={0.2} />
              <stop offset="95%" stopColor={COLORS.covered} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
          <XAxis dataKey="fecha" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => (v / 1000).toFixed(0) + 'K'} />
          <Tooltip
            formatter={(v, name) => [v.toLocaleString('es-CO'), name]}
            labelStyle={{ fontWeight: 600 }}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Area
            type="monotone"
            dataKey="total"
            name="Total"
            stroke="#3b82f6"
            fill="url(#gTotal)"
            strokeWidth={2}
          />
          <Area
            type="monotone"
            dataKey="cubiertos"
            name="Cubiertos"
            stroke={COLORS.covered}
            fill="url(#gCubiertos)"
            strokeWidth={2}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── Horizontal bar: top servicios ────────────────────────────────────────────
export function TopServicesChart({ data }) {
  const top10 = data.slice(0, 10).reverse()

  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">Top 10 Servicios Solicitados</h3>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart
          data={top10}
          layout="vertical"
          margin={{ top: 0, right: 60, left: 8, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={(v) => (v / 1000).toFixed(0) + 'K'} />
          <YAxis
            type="category"
            dataKey="servicio_solicitado"
            tick={{ fontSize: 9 }}
            width={160}
            tickFormatter={(v) => (v.length > 28 ? v.slice(0, 28) + '…' : v)}
          />
          <Tooltip
            formatter={(v) => v.toLocaleString('es-CO')}
            labelStyle={{ fontWeight: 600, fontSize: 12 }}
          />
          <Bar dataKey="total" name="Solicitudes" fill="#3b82f6" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── Valor cubierto por perfil ────────────────────────────────────────────────
export function ValorPerfilChart({ data }) {
  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">Valor Cubierto por Perfil</h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
          <XAxis dataKey="perfil_cobertura" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 10 }} tickFormatter={fmt} />
          <Tooltip formatter={(v) => ['$' + v.toLocaleString('es-CO'), 'Valor cubierto']} />
          <Bar dataKey="valor_cubierto" name="Valor cubierto" radius={[4, 4, 0, 0]}>
            {data.map((entry) => (
              <Cell key={entry.perfil_cobertura} fill={PERFIL_COLORS[entry.perfil_cobertura] || '#94a3b8'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
