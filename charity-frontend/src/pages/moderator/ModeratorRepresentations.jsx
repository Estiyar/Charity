import { useEffect, useState } from 'react'
import { confirmRepresentation, fetchModerationRepresentations, rejectRepresentation } from '../../api/client'
import {
  formatDateTime,
  relationshipLabel,
  representationMethodLabel,
  representationStatusLabel,
} from '../../utils/format'

export default function ModeratorRepresentations() {
  const [items, setItems] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  function load() {
    setLoading(true)
    fetchModerationRepresentations()
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  async function approve(id) {
    setError('')
    try {
      await confirmRepresentation(id)
      load()
    } catch {
      setError('Не удалось подтвердить представительство.')
    }
  }

  async function reject(id) {
    const reason = window.prompt('Причина отклонения')
    if (!reason?.trim()) return
    setError('')
    try {
      await rejectRepresentation(id, reason.trim())
      load()
    } catch (err) {
      setError(err.data?.detail || 'Не удалось отклонить представительство.')
    }
  }

  if (loading) {
    return <div className="rounded-3xl bg-white p-8 text-slate-500 shadow-md">Загрузка...</div>
  }

  return (
    <section className="rounded-3xl bg-white p-6 shadow-md">
      <h1 className="mb-6 text-2xl font-semibold text-slate-800">Представительство</h1>
      {error ? <p className="mb-4 text-sm text-red-600">{error}</p> : null}
      {!items.length ? (
        <p className="text-slate-500">Заявок нет</p>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <article key={item.id} className="rounded-2xl bg-sky-50 p-4">
              <p className="font-medium text-slate-800">{item.beneficiary_name}</p>
              <p className="text-sm text-slate-500">
                Автор #{item.author_id} · {relationshipLabel(item.relationship_type)} · {representationMethodLabel(item.verification_method)}
              </p>
              <p className="text-xs text-slate-400">
                {representationStatusLabel(item.verification_status)} · {formatDateTime(item.updated_at)}
              </p>
              {item.document_ids?.length ? (
                <p className="text-xs text-slate-500">Документы: {item.document_ids.join(', ')}</p>
              ) : null}
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => approve(item.id)}
                  className="rounded-2xl bg-teal-500 px-4 py-2 text-sm font-semibold text-white"
                >
                  Подтвердить
                </button>
                <button
                  type="button"
                  onClick={() => reject(item.id)}
                  className="rounded-2xl border border-red-200 px-4 py-2 text-sm font-semibold text-red-700"
                >
                  Отклонить
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
