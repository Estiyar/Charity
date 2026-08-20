import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchCard, fetchCardHistory, fetchCardInvoices, fetchExpenses } from '../../api/client'
import AuthorDocuments from '../../components/AuthorDocuments'
import AuthorRevisionPanel from '../../components/AuthorRevisionPanel'
import CardTimeline from '../../components/CardTimeline'
import EscrowBlock from '../../components/EscrowBlock'
import ExpenseForm from '../../components/ExpenseForm'
import ExpenseHistory from '../../components/ExpenseHistory'
import InvoiceForm from '../../components/InvoiceForm'
import InvoiceHistory from '../../components/InvoiceHistory'
import ProgressBar from '../../components/ProgressBar'
import TrustBadges from '../../components/TrustBadges'
import { formatDate, formatMoney, statusBadgeClass, statusLabel } from '../../utils/format'

const EXPENSE_CARD_STATUSES = new Set(['active', 'completed'])

export default function AuthorFundraiserDetail() {
  const { id } = useParams()
  const [card, setCard] = useState(null)
  const [expenses, setExpenses] = useState([])
  const [invoices, setInvoices] = useState([])
  const [history, setHistory] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const loadData = useCallback(() => {
    setLoading(true)
    setError('')
    Promise.all([
      fetchCard(id),
      fetchExpenses(id).catch(() => []),
      fetchCardInvoices(id).catch(() => []),
      fetchCardHistory(id).catch(() => []),
    ])
      .then(([cardData, expenseItems, invoiceItems, historyItems]) => {
        setCard(cardData)
        setExpenses(expenseItems)
        setInvoices(invoiceItems)
        setHistory(historyItems)
      })
      .catch(() => {
        setCard(null)
        setExpenses([])
        setInvoices([])
        setError('Сбор не найден или недоступен.')
      })
      .finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    loadData()
  }, [loadData])

  function refreshAfterExpense() {
    fetchCard(id).then(setCard).catch(() => {})
    fetchExpenses(id).then(setExpenses).catch(() => setExpenses([]))
    fetchCardInvoices(id).then(setInvoices).catch(() => setInvoices([]))
  }

  if (loading) {
    return (
      <div className="rounded-3xl bg-white p-8 text-center text-slate-500 shadow-md">
        Загрузка...
      </div>
    )
  }

  if (error || !card) {
    return (
      <div className="space-y-4">
        <Link to="/author" className="text-sm font-medium text-teal-600 hover:underline">
          ← Мои сборы
        </Link>
        <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>
      </div>
    )
  }

  const canManageExpenses = EXPENSE_CARD_STATUSES.has(card.status)

  return (
    <div className="space-y-6">
      <Link to="/author" className="text-sm font-medium text-teal-600 hover:underline">
        ← Мои сборы
      </Link>

      <section className="rounded-3xl bg-white p-6 shadow-md">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-2xl font-semibold text-slate-800">{card.full_name}</h2>
              <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(card.status)}`}>
                {statusLabel(card.status)}
              </span>
            </div>
            {card.duplicate_suspected ? (
              <p className="rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-900">
                Сбор отправлен на ручную проверку из-за возможных совпадений с другими карточками.
              </p>
            ) : null}
            <p className="text-sm text-slate-500">{card.diagnosis} · {card.city}</p>
            <p className="text-sm text-slate-500">До {formatDate(card.end_date)}</p>
          </div>
          {['active', 'completed', 'redistribution'].includes(card.status) && (
            <Link
              to={`/cards/${card.id}`}
              className="rounded-2xl border border-sky-200 px-4 py-2 text-sm text-slate-600 hover:bg-sky-50"
            >
              Публичная страница
            </Link>
          )}
        </div>
        <div className="mt-4">
          <div className="mb-2 flex justify-between text-sm">
            <span className="font-semibold text-slate-800">
              {formatMoney(card.collected_amount)} собрано
            </span>
            <span className="text-slate-500">Цель {formatMoney(card.target_amount)}</span>
          </div>
          <ProgressBar percent={card.progress_percent} />
        </div>
        {card.moderator_comment && card.status !== 'revision_required' && (
          <div className="mt-4 rounded-2xl bg-amber-50 p-4 text-sm text-slate-700">
            <p className="font-medium text-slate-800">Комментарий модератора</p>
            <p>{card.moderator_comment}</p>
          </div>
        )}
      </section>

      <AuthorRevisionPanel card={card} onUpdated={loadData} />

      <TrustBadges trustStatus={card.trust_status} />
      <CardTimeline events={history} />
      <AuthorDocuments cardId={card.id} cardStatus={card.status} />

      {canManageExpenses ? (
        <div className="space-y-6">
          <EscrowBlock card={card} showFundraiserName />
          <div className="grid gap-6 lg:grid-cols-2">
            <ExpenseForm cardId={card.id} onSuccess={refreshAfterExpense} />
            <ExpenseHistory expenses={expenses} onChanged={refreshAfterExpense} />
            <InvoiceForm cardId={card.id} onSuccess={refreshAfterExpense} />
            <InvoiceHistory invoices={invoices} onChanged={refreshAfterExpense} />
          </div>
        </div>
      ) : (
        <div className="rounded-3xl bg-white p-6 text-sm text-slate-600 shadow-md">
          Эскроу-счёт и расходы доступны после одобрения и активации сбора.
        </div>
      )}
    </div>
  )
}
