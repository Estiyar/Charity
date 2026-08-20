import { formatDateTime } from '../utils/format'

export default function CardTimeline({ events, staff = false }) {
  const items = events || []
  return (
    <section className="rounded-3xl bg-white p-6 shadow-md">
      <h2 className="text-xl font-semibold text-slate-800">История изменений</h2>
      {items.length ? (
        <ul className="mt-4 space-y-3">
          {items.map((item) => (
            <li key={item.id} className="rounded-2xl bg-sky-50 px-4 py-3 text-sm text-slate-700">
              <p className="font-medium text-slate-800">{item.summary}</p>
              <p className="text-xs text-slate-500">{formatDateTime(item.created_at)}</p>
              {staff && item.actor_role ? (
                <p className="mt-1 text-xs text-slate-500">Роль: {item.actor_role}</p>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm text-slate-500">Записей пока нет.</p>
      )}
    </section>
  )
}
