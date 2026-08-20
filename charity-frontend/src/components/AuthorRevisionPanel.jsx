import { useState } from 'react'
import { submitCard, updateCard } from '../api/client'
import { CommentHistory } from './ModeratorCommentFields'

export default function AuthorRevisionPanel({ card, onUpdated }) {
  const [description, setDescription] = useState(card.description || '')
  const [clinic, setClinic] = useState(card.clinic || '')
  const [diagnosis, setDiagnosis] = useState(card.diagnosis || '')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  if (card.status !== 'revision_required') {
    return card.comments?.length ? (
      <section className="rounded-3xl bg-white p-6 shadow-md">
        <h2 className="mb-3 text-lg font-semibold text-slate-800">Комментарии модератора</h2>
        <CommentHistory comments={card.comments} />
      </section>
    ) : null
  }

  async function saveAndResubmit() {
    setError('')
    setLoading(true)
    try {
      await updateCard(card.id, { description, clinic, diagnosis })
      await submitCard(card.id)
      onUpdated?.()
    } catch (err) {
      setError(err.data?.detail || 'Не удалось сохранить и отправить карточку.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="rounded-3xl bg-white p-6 shadow-md">
      <h2 className="text-xl font-semibold text-slate-800">Доработка сбора</h2>
      <p className="mt-2 text-sm text-amber-800">
        {card.moderator_comment || 'Модератор запросил изменения. Исправьте поля и отправьте снова.'}
      </p>
      {card.comments?.length ? (
        <div className="mt-4">
          <CommentHistory comments={card.comments} />
        </div>
      ) : null}
      <div className="mt-4 space-y-3">
        <textarea
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm"
          rows={4}
        />
        <input
          value={diagnosis}
          onChange={(event) => setDiagnosis(event.target.value)}
          className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm"
          placeholder="Диагноз"
        />
        <input
          value={clinic}
          onChange={(event) => setClinic(event.target.value)}
          className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm"
          placeholder="Клиника"
        />
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        <button
          type="button"
          disabled={loading}
          onClick={saveAndResubmit}
          className="rounded-2xl bg-amber-500 px-4 py-3 text-sm font-semibold text-white disabled:opacity-60"
        >
          Сохранить и отправить снова
        </button>
      </div>
    </section>
  )
}
