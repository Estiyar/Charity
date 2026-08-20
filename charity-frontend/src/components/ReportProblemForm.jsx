import { useState } from 'react'
import { submitCardReport } from '../api/client'

const categories = [
  { value: 'suspected_fraud', label: 'Подозрение на мошенничество' },
  { value: 'incorrect_information', label: 'Неверная информация' },
  { value: 'stolen_photos', label: 'Чужие / несанкционированные фото' },
  { value: 'outdated_fundraiser', label: 'Сбор уже завершён или устарел' },
  { value: 'document_issue', label: 'Проблема с документами' },
  { value: 'other', label: 'Другое' },
]

export default function ReportProblemForm({ cardId, onSubmitted }) {
  const [category, setCategory] = useState(categories[0].value)
  const [description, setDescription] = useState('')
  const [attachment, setAttachment] = useState(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSuccess('')
    setSubmitting(true)
    try {
      await submitCardReport(cardId, { category, description, attachment })
      setSuccess('Жалоба отправлена в очередь модерации.')
      setDescription('')
      setAttachment(null)
      event.target.reset()
      onSubmitted?.()
    } catch (err) {
      setError(err.message || 'Не удалось отправить жалобу.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="rounded-3xl bg-white p-6 shadow-md">
      <h2 className="text-xl font-semibold text-slate-800">Сообщить о проблеме</h2>
      <p className="mt-2 text-sm text-slate-600">
        Жалоба попадёт в очередь модерации. Повторные жалобы от одного пользователя не увеличивают риск.
      </p>
      <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
        <label className="block text-sm font-medium text-slate-700">
          Категория
          <select
            value={category}
            onChange={(event) => setCategory(event.target.value)}
            className="mt-1 w-full rounded-2xl border border-sky-100 px-4 py-3"
          >
            {categories.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm font-medium text-slate-700">
          Описание
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            required
            minLength={10}
            rows={4}
            className="mt-1 w-full rounded-2xl border border-sky-100 px-4 py-3"
            placeholder="Опишите проблему подробно"
          />
        </label>
        <label className="block text-sm font-medium text-slate-700">
          Вложение (необязательно)
          <input
            type="file"
            onChange={(event) => setAttachment(event.target.files?.[0] || null)}
            className="mt-1 block w-full text-sm text-slate-600"
          />
        </label>
        {error ? <p className="text-sm text-rose-600">{error}</p> : null}
        {success ? <p className="text-sm text-teal-700">{success}</p> : null}
        <button
          type="submit"
          disabled={submitting}
          className="rounded-2xl bg-teal-500 px-5 py-3 text-sm font-semibold text-white disabled:opacity-60"
        >
          {submitting ? 'Отправка…' : 'Отправить жалобу'}
        </button>
      </form>
    </section>
  )
}
