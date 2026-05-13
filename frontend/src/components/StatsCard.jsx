export default function StatsCard({ title, value, subtitle, icon: Icon, color = 'blue' }) {
  const colors = {
    blue:    { bg: 'bg-blue-50',    icon: 'text-blue-600',    border: 'border-blue-100' },
    emerald: { bg: 'bg-emerald-50', icon: 'text-emerald-600', border: 'border-emerald-100' },
    red:     { bg: 'bg-red-50',     icon: 'text-red-600',     border: 'border-red-100' },
    violet:  { bg: 'bg-violet-50',  icon: 'text-violet-600',  border: 'border-violet-100' },
    amber:   { bg: 'bg-amber-50',   icon: 'text-amber-600',   border: 'border-amber-100' },
  }

  const c = colors[color] || colors.blue

  return (
    <div className="card p-5">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-500 font-medium truncate">{title}</p>
          <p className="mt-1 text-2xl font-bold text-gray-900 truncate">{value ?? '—'}</p>
          {subtitle && <p className="mt-1 text-xs text-gray-400 truncate">{subtitle}</p>}
        </div>
        {Icon && (
          <div className={`ml-3 flex-shrink-0 w-10 h-10 rounded-lg ${c.bg} ${c.border} border flex items-center justify-center`}>
            <Icon className={`w-5 h-5 ${c.icon}`} />
          </div>
        )}
      </div>
    </div>
  )
}
