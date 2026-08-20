import { formatDateTime } from '../utils/format'

export default function TrustBadges({ trustStatus }) {
  const badges = (trustStatus?.badges || []).filter((badge) => badge && badge.verified === true)
  if (!badges.length && !trustStatus?.last_verified_at) {
    return null
  }

  return (
    <section className="rounded-3xl bg-white p-6 shadow-md">
      <h2 className="text-xl font-semibold text-slate-800">Признаки доверия</h2>
      {badges.length ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {badges.map((badge) => (
            <span
              key={badge.code}
              className="rounded-full bg-mint-100 px-3 py-1 text-sm font-medium text-teal-800"
            >
              {badge.label}
            </span>
          ))}
        </div>
      ) : (
        <p className="mt-3 text-sm text-slate-500">Подтверждённые статусы пока отсутствуют.</p>
      )}
      {trustStatus?.last_verified_at ? (
        <p className="mt-3 text-xs text-slate-500">
          Последняя проверка: {formatDateTime(trustStatus.last_verified_at)}
        </p>
      ) : null}
    </section>
  )
}
