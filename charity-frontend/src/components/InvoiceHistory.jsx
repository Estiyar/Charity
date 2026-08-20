import { useState } from 'react'
import { cancelInvoice } from '../api/client'
import { formatDate, formatMoney, invoiceStatusLabel } from '../utils/format'

export default function InvoiceHistory({ invoices, onChanged }) {
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState(null)

  if (!invoices.length) {
    return (
      <div className="rounded-3xl bg-white p-6 text-sm text-slate-500 shadow-md">
        Счетов на прямую выплату пока нет.
      </div>
    )
  }

  async function handleCancel(invoiceId) {
    setError('')
    setBusyId(invoiceId)
    try {
      await cancelInvoice(invoiceId)
      onChanged?.()
    } catch (err) {
      setError(err.data?.detail || 'Не удалось отменить счёт.')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="overflow-hidden rounded-3xl bg-white p-6 shadow-md">
      <h3 className="mb-4 text-lg font-semibold text-slate-800">Счета клиникам</h3>
      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="border-b border-sky-100 text-slate-500">
              <th className="py-2 pr-4">Дата</th>
              <th className="py-2 pr-4">Организация</th>
              <th className="py-2 pr-4">Сумма</th>
              <th className="py-2 pr-4">Статус</th>
              <th className="py-2">Реквизиты</th>
            </tr>
          </thead>
          <tbody>
            {invoices.map((invoice) => (
              <tr key={invoice.id} className="border-b border-sky-50 align-top">
                <td className="py-3 pr-4">{formatDate(invoice.date)}</td>
                <td className="py-3 pr-4">{invoice.organization?.name || invoice.purpose}</td>
                <td className="py-3 pr-4">{formatMoney(invoice.amount)}</td>
                <td className="py-3 pr-4">
                  <p>{invoiceStatusLabel(invoice.status)}</p>
                  {invoice.status === 'pending_verification' && (
                    <button
                      type="button"
                      disabled={busyId === invoice.id}
                      onClick={() => handleCancel(invoice.id)}
                      className="mt-1 text-xs text-red-600 hover:underline disabled:opacity-60"
                    >
                      Отменить
                    </button>
                  )}
                </td>
                <td className="py-3 text-xs text-slate-500">
                  БИН {invoice.organization?.bin_masked || '—'}
                  <br />
                  {invoice.organization?.iban_masked || '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
