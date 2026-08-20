import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchInvoice, fetchInvoiceOriginalBlob, rejectInvoice, verifyInvoice } from '../../api/client'
import { formatDate, formatMoney, invoiceStatusLabel, payoutStatusLabel } from '../../utils/format'

export default function ModeratorInvoiceReview() {
  const { id } = useParams()
  const [invoice, setInvoice] = useState(null)
  const [comment, setComment] = useState('')
  const [originalUrl, setOriginalUrl] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let active = true
    fetchInvoice(id)
      .then((item) => {
        if (!active) return
        setInvoice(item)
        if (item.original_url) {
          return fetchInvoiceOriginalBlob(item.id).then((url) => {
            if (active) setOriginalUrl(url)
          })
        }
        return null
      })
      .catch(() => {
        if (active) setInvoice(null)
      })
    return () => {
      active = false
    }
  }, [id])

  async function runAction(action) {
    setError('')
    setLoading(true)
    try {
      if (action === 'verify') await verifyInvoice(id, comment)
      else await rejectInvoice(id, comment)
      window.location.href = '/moderator/invoices'
    } catch (err) {
      setError(err.data?.comment?.[0] || err.data?.detail || 'Не удалось выполнить действие.')
    } finally {
      setLoading(false)
    }
  }

  if (!invoice) {
    return (
      <div className="rounded-3xl bg-white p-8 text-center text-slate-500 shadow-md">
        Счёт не найден или уже обработан.
        <div className="mt-4">
          <Link to="/moderator/invoices" className="text-teal-600 hover:underline">← К списку счетов</Link>
        </div>
      </div>
    )
  }

  const organization = invoice.organization || {}

  return (
    <div className="space-y-6">
      <Link to="/moderator/invoices" className="text-sm font-medium text-teal-600 hover:underline">
        ← Счета на проверке
      </Link>
      <section className="rounded-3xl bg-white p-6 shadow-md">
        <h1 className="text-2xl font-semibold text-slate-800">Проверка счёта и получателя</h1>
        <div className="mt-4 grid gap-3 text-sm text-slate-700 sm:grid-cols-2">
          <p><span className="font-medium">Организация:</span> {organization.name}</p>
          <p><span className="font-medium">БИН:</span> {organization.bin_masked || '—'}</p>
          <p><span className="font-medium">IBAN:</span> {organization.iban_masked || '—'}</p>
          <p><span className="font-medium">Банк:</span> {organization.bank_name || '—'}</p>
          <p><span className="font-medium">Сумма:</span> {formatMoney(invoice.amount)} {invoice.currency}</p>
          <p><span className="font-medium">Дата:</span> {formatDate(invoice.date)}</p>
          <p><span className="font-medium">Статус счёта:</span> {invoiceStatusLabel(invoice.status)}</p>
        </div>
        {(invoice.payouts || []).map((payout) => (
          <p key={payout.id} className="mt-3 text-sm text-slate-600">
            Выплата #{payout.id}: {payoutStatusLabel(payout.status)} · {formatMoney(payout.amount)}
          </p>
        ))}
        {originalUrl && (
          <iframe title="Счёт" src={originalUrl} className="mt-4 h-96 w-full rounded-2xl border border-sky-100" />
        )}
      </section>
      {invoice.status === 'pending_verification' && (
        <section className="rounded-3xl bg-white p-6 shadow-md">
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Комментарий модератора"
            rows={4}
            className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
          />
          {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
          <div className="mt-4 flex flex-wrap gap-3">
            <button type="button" disabled={loading} onClick={() => runAction('verify')} className="rounded-2xl bg-teal-500 px-5 py-3 text-sm font-semibold text-white disabled:opacity-60">
              Подтвердить организацию и сумму
            </button>
            <button type="button" disabled={loading} onClick={() => runAction('reject')} className="rounded-2xl bg-red-500 px-5 py-3 text-sm font-semibold text-white disabled:opacity-60">
              Отклонить
            </button>
          </div>
        </section>
      )}
    </div>
  )
}
