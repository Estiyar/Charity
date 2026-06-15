import { useState } from 'react'
import { createExpense } from '../api/client'

const initialForm = {
  date: '',
  purpose: '',
  amount: '',
  comment: '',
}

export default function ExpenseForm({ cardId, onSuccess }) {
  const [form, setForm] = useState(initialForm)
  const [file, setFile] = useState(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSuccess('')
    setLoading(true)
    try {
      const payload = new FormData()
      payload.append('date', form.date)
      payload.append('purpose', form.purpose)
      payload.append('amount', form.amount)
      if (form.comment) payload.append('comment', form.comment)
      if (file) payload.append('file', file)
      await createExpense(cardId, payload)
      setForm(initialForm)
      setFile(null)
      setSuccess('Расход отправлен на проверку модератору.')
      onSuccess?.()
    } catch (err) {
      const data = err.data || {}
      setError(
        data.amount?.[0]
          || data.purpose?.[0]
          || data.file?.[0]
          || data.detail
          || 'Не удалось добавить расход.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-3xl bg-white p-6 shadow-md">
      <h3 className="text-lg font-semibold text-slate-800">Добавить расход</h3>
      <input
        type="date"
        value={form.date}
        onChange={(e) => updateField('date', e.target.value)}
        required
        className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
      />
      <input
        type="text"
        placeholder="Назначение"
        value={form.purpose}
        onChange={(e) => updateField('purpose', e.target.value)}
        required
        className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
      />
      <input
        type="number"
        min="0.01"
        step="0.01"
        placeholder="Сумма"
        value={form.amount}
        onChange={(e) => updateField('amount', e.target.value)}
        required
        className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
      />
      <textarea
        placeholder="Комментарий"
        value={form.comment}
        onChange={(e) => updateField('comment', e.target.value)}
        rows={3}
        className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
      />
      <input
        type="file"
        accept=".pdf,.jpg,.jpeg,.png"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
        className="w-full text-sm text-slate-600"
      />
      {error && <p className="text-sm text-red-600">{error}</p>}
      {success && <p className="rounded-2xl bg-mint-100 px-4 py-3 text-sm text-teal-700">{success}</p>}
      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-2xl bg-teal-500 px-6 py-3 font-semibold text-white hover:bg-teal-600 disabled:opacity-60"
      >
        {loading ? 'Отправка...' : 'Отправить на проверку'}
      </button>
    </form>
  )
}
