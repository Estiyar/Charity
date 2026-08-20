import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchManualReviews } from '../../api/client'
import { formatDateTime, statusLabel } from '../../utils/format'

const SUBJECT_LABELS = {
  user: 'Пользователь',
  card: 'Карточка',
}

export default function ManualReviewQueue() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [subjectType, setSubjectType] = useState('')

  useEffect(() => {
    setLoading(true)
    fetchManualReviews({
      status: 'open',
      subject_type: subjectType || undefined,
    })
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [subjectType])

  if (loading) {
    return <div className="rounded-3xl bg-white p-8 text-slate-500 shadow-md">Загрузка...</div>
  }

  return (
    <section className="rounded-3xl bg-white p-6 shadow-md">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-slate-800">Высокий риск</h1>
        <select
          value={subjectType}
          onChange={(event) => setSubjectType(event.target.value)}
          className="rounded-2xl border border-slate-200 px-3 py-2 text-sm"
        >
          <option value="">Все типы</option>
          <option value="user">Пользователи</option>
          <option value="card">Карточки</option>
        </select>
      </div>
      {!items.length ? (
        <p className="text-slate-500">Очередь пуста</p>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <div key={item.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-rose-50 p-4">
              <div>
                <p className="font-medium text-slate-800">{item.subject_label}</p>
                <p className="text-sm text-slate-500">
                  {SUBJECT_LABELS[item.subject_type] || item.subject_type} #{item.subject_id}
                  {' · '}
                  {item.risk_level || '—'} · {item.risk_score}
                </p>
                <p className="text-xs text-slate-400">
                  {statusLabel(item.status)} · {formatDateTime(item.opened_at)}
                </p>
              </div>
              <Link
                to={`/moderator/reviews/${item.id}`}
                className="rounded-2xl bg-teal-500 px-4 py-2 text-sm font-semibold text-white"
              >
                Проверить
              </Link>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
