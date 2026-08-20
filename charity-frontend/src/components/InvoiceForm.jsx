import { useState } from 'react'
import { createInvoice } from '../api/client'
import FileUploadField from './FileUploadField'

const initialForm = {
  date: '',
  amount: '',
  organization_name: '',
  organization_bin: '',
  organization_kind: 'clinic',
  iban: '',
  bank_name: '',
  number: '',
  comment: '',
}

export default function InvoiceForm({ cardId, onSuccess }) {
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
      Object.entries(form).forEach(([key, value]) => {
        if (value) payload.append(key, value)
      })
      if (file) payload.append('file', file)
      await createInvoice(cardId, payload)
      setForm(initialForm)
      setFile(null)
      setSuccess('Счёт отправлен на проверку. Выплата будет создана после подтверждения модератором.')
      onSuccess?.()
    } catch (err) {
      const data = err.data || {}
      setError(data.amount?.[0] || data.file?.[0] || data.iban?.[0] || data.detail || 'Не удалось отправить счёт.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-3xl bg-white p-6 shadow-md">
      <h3 className="text-lg font-semibold text-slate-800">Прямая оплата клинике</h3>
      <input type="date" value={form.date} onChange={(e) => updateField('date', e.target.value)} required className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500" />
      <select value={form.organization_kind} onChange={(e) => updateField('organization_kind', e.target.value)} className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500">
        <option value="clinic">Клиника</option>
        <option value="supplier">Поставщик</option>
      </select>
      <input type="text" placeholder="Название организации" value={form.organization_name} onChange={(e) => updateField('organization_name', e.target.value)} required className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500" />
      <input type="text" placeholder="БИН" value={form.organization_bin} onChange={(e) => updateField('organization_bin', e.target.value)} required className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500" />
      <input type="text" placeholder="IBAN" value={form.iban} onChange={(e) => updateField('iban', e.target.value)} required className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500" />
      <input type="text" placeholder="Банк" value={form.bank_name} onChange={(e) => updateField('bank_name', e.target.value)} className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500" />
      <input type="text" placeholder="Номер счёта" value={form.number} onChange={(e) => updateField('number', e.target.value)} className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500" />
      <input type="number" min="0.01" step="0.01" placeholder="Сумма" value={form.amount} onChange={(e) => updateField('amount', e.target.value)} required className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500" />
      <textarea placeholder="Комментарий" value={form.comment} onChange={(e) => updateField('comment', e.target.value)} rows={3} className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500" />
      <FileUploadField
        id={`invoice-file-${cardId}`}
        accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
        label="Счёт PDF, JPG или PNG"
        files={file}
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      {error && <p className="text-sm text-red-600">{error}</p>}
      {success && <p className="rounded-2xl bg-mint-100 px-4 py-3 text-sm text-teal-700">{success}</p>}
      <button type="submit" disabled={loading} className="w-full rounded-2xl bg-teal-500 px-6 py-3 font-semibold text-white hover:bg-teal-600 disabled:opacity-60">
        {loading ? 'Отправка...' : 'Отправить счёт на проверку'}
      </button>
    </form>
  )
}
