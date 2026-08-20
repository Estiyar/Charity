import { useEffect, useState } from 'react'
import {
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  markNotificationUnread,
} from '../api/client'
import { formatDate } from '../utils/format'

export default function Notifications() {
  const [page, setPage] = useState(1)
  const [items, setItems] = useState([])
  const [count, setCount] = useState(0)
  const [unreadCount, setUnreadCount] = useState(0)
  const [nextPage, setNextPage] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  function load(targetPage = page) {
    setLoading(true)
    setError('')
    fetchNotifications({ page: targetPage })
      .then((data) => {
        setItems(data.results || [])
        setCount(data.count || 0)
        setUnreadCount(data.unread_count || 0)
        setNextPage(Boolean(data.next))
      })
      .catch((err) => setError(err.message || 'Не удалось загрузить уведомления.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load(page)
  }, [page])

  async function toggleRead(item) {
    setSaving(true)
    try {
      if (item.is_read) {
        await markNotificationUnread(item.id)
      } else {
        await markNotificationRead(item.id)
      }
      load(page)
    } finally {
      setSaving(false)
    }
  }

  async function handleReadAll() {
    setSaving(true)
    try {
      await markAllNotificationsRead()
      load(page)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <section className="rounded-3xl bg-white p-6 shadow-md">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-800">Уведомления</h1>
            <p className="mt-1 text-sm text-slate-500">
              Всего: {count} · Непрочитанных: {unreadCount}
            </p>
          </div>
          <button
            type="button"
            disabled={saving || unreadCount === 0}
            onClick={handleReadAll}
            className="rounded-2xl border border-sky-200 px-4 py-2 text-sm text-slate-600 disabled:opacity-60"
          >
            Отметить всё как прочитанное
          </button>
        </div>
        {error ? <p className="mt-4 text-sm text-rose-600">{error}</p> : null}
        {loading ? (
          <p className="mt-6 text-sm text-slate-500">Загрузка...</p>
        ) : !items.length ? (
          <p className="mt-6 text-sm text-slate-500">Уведомлений пока нет.</p>
        ) : (
          <div className="mt-6 space-y-3">
            {items.map((item) => (
              <article
                key={item.id}
                className={`rounded-2xl border px-4 py-4 ${
                  item.is_read ? 'border-slate-200 bg-slate-50' : 'border-teal-200 bg-mint-100'
                }`}
              >
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="text-base font-semibold text-slate-800">{item.title}</h2>
                      <span className="rounded-full bg-white px-3 py-1 text-xs text-slate-500">
                        {item.type}
                      </span>
                    </div>
                    <p className="text-sm text-slate-600">{item.body}</p>
                    <p className="text-xs text-slate-500">
                      Создано: {formatDate(item.created_at)}
                      {item.read_at ? ` · Прочитано: ${formatDate(item.read_at)}` : ''}
                    </p>
                    {item.deep_link ? (
                      <a href={item.deep_link} className="text-sm font-medium text-teal-700 hover:underline">
                        Перейти
                      </a>
                    ) : null}
                    {item.deliveries?.length ? (
                      <div className="flex flex-wrap gap-2">
                        {item.deliveries.map((delivery) => (
                          <span key={delivery.id} className="rounded-full bg-white px-3 py-1 text-xs text-slate-500">
                            {delivery.channel}: {delivery.status}
                          </span>
                        ))}
                      </div>
                    ) : null}
                  </div>
                  <button
                    type="button"
                    disabled={saving}
                    onClick={() => toggleRead(item)}
                    className="rounded-2xl border border-sky-200 px-4 py-2 text-sm text-slate-600 disabled:opacity-60"
                  >
                    {item.is_read ? 'Пометить непрочитанным' : 'Отметить прочитанным'}
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
        <div className="mt-6 flex items-center justify-between">
          <button
            type="button"
            disabled={page <= 1 || loading}
            onClick={() => setPage((value) => Math.max(1, value - 1))}
            className="rounded-2xl border border-sky-200 px-4 py-2 text-sm text-slate-600 disabled:opacity-60"
          >
            Назад
          </button>
          <span className="text-sm text-slate-500">Страница {page}</span>
          <button
            type="button"
            disabled={!nextPage || loading}
            onClick={() => setPage((value) => value + 1)}
            className="rounded-2xl border border-sky-200 px-4 py-2 text-sm text-slate-600 disabled:opacity-60"
          >
            Дальше
          </button>
        </div>
      </section>
    </div>
  )
}
