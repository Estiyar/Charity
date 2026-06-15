import { formatMoney } from '../utils/format'

const items = [
  { key: 'active_fundraisers', label: 'Активные сборы' },
  { key: 'total_collected', label: 'Собрано всего', format: formatMoney },
  { key: 'donors_count', label: 'Доноры' },
  { key: 'verified_documents', label: 'Проверенные документы' },
]

export default function StatsBlock({ stats }) {
  return (
    <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {items.map((item) => {
        const raw = stats?.[item.key] ?? 0
        const value = item.format ? item.format(raw) : raw
        return (
          <div
            key={item.key}
            className="rounded-3xl bg-white p-6 text-center shadow-md"
          >
            <p className="text-3xl font-bold text-teal-600">{value}</p>
            <p className="mt-2 text-sm text-slate-600">{item.label}</p>
          </div>
        )
      })}
    </section>
  )
}
