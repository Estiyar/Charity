import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchModerationCards, fetchModerationDocuments, fetchModerationExpenses } from '../../api/client'
import { expenseStatusLabel, formatDate, formatMoney, statusLabel } from '../../utils/format'

export default function ModeratorList({ status, title, documentsMode = false, expensesMode = false }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    const loader = documentsMode
      ? fetchModerationDocuments()
      : expensesMode
        ? fetchModerationExpenses()
        : fetchModerationCards(status)
    loader
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [status, documentsMode, expensesMode])

  if (loading) {
    return <div className="rounded-3xl bg-white p-8 text-slate-500 shadow-md">Загрузка...</div>
  }

  return (
    <section className="rounded-3xl bg-white p-6 shadow-md">
      <h1 className="mb-6 text-2xl font-semibold text-slate-800">{title}</h1>
      {!items.length ? (
        <p className="text-slate-500">Записей нет</p>
      ) : documentsMode ? (
        <div className="space-y-3">
          {items.map((doc) => (
            <div key={doc.id} className="flex items-center justify-between rounded-2xl bg-sky-50 p-4">
              <div>
                <p className="font-medium text-slate-800">{doc.file_name}</p>
                <p className="text-sm text-slate-500">Карточка #{doc.card_id} · {doc.file_type}</p>
              </div>
              <Link
                to={`/moderator/cards/${doc.card_id}`}
                className="rounded-2xl bg-teal-500 px-4 py-2 text-sm font-semibold text-white"
              >
                Проверить
              </Link>
            </div>
          ))}
        </div>
      ) : expensesMode ? (
        <div className="space-y-3">
          {items.map((expense) => (
            <div key={expense.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-sky-50 p-4">
              <div>
                <p className="font-medium text-slate-800">{expense.purpose}</p>
                <p className="text-sm text-slate-500">
                  {expense.card_name} · {formatMoney(expense.amount)} · {expenseStatusLabel(expense.status)}
                </p>
                <p className="text-xs text-slate-400">{formatDate(expense.date)}</p>
              </div>
              <Link
                to={`/moderator/expenses/${expense.id}`}
                className="rounded-2xl bg-teal-500 px-4 py-2 text-sm font-semibold text-white"
              >
                Проверить
              </Link>
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((card) => (
            <div key={card.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-sky-50 p-4">
              <div>
                <p className="font-medium text-slate-800">{card.full_name}</p>
                <p className="text-sm text-slate-500">
                  {card.diagnosis} · {card.city} · {statusLabel(card.status)}
                </p>
                <p className="text-xs text-slate-400">До {formatDate(card.end_date)}</p>
              </div>
              <Link
                to={`/moderator/cards/${card.id}`}
                className="rounded-2xl bg-teal-500 px-4 py-2 text-sm font-semibold text-white"
              >
                Открыть
              </Link>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
