import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  approveExpense,
  fetchModerationExpenses,
  mediaUrl,
  rejectExpense,
  requestExpenseClarification,
} from '../../api/client'
import { expenseStatusLabel, formatDate, formatMoney } from '../../utils/format'

export default function ModeratorExpenseReview() {
  const { id } = useParams()
  const [expense, setExpense] = useState(null)
  const [comment, setComment] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchModerationExpenses()
      .then((items) => setExpense(items.find((item) => String(item.id) === id) || null))
      .catch(() => setExpense(null))
  }, [id])

  async function runAction(action) {
    setError('')
    setLoading(true)
    try {
      const handlers = {
        approve: () => approveExpense(id, comment),
        reject: () => rejectExpense(id, comment),
        clarify: () => requestExpenseClarification(id, comment),
      }
      await handlers[action]()
      window.location.href = '/moderator/expenses'
    } catch (err) {
      setError(err.data?.comment?.[0] || err.data?.detail || 'Не удалось выполнить действие.')
    } finally {
      setLoading(false)
    }
  }

  if (!expense) {
    return (
      <div className="rounded-3xl bg-white p-8 text-center text-slate-500 shadow-md">
        Расход не найден или уже обработан.
        <div className="mt-4">
          <Link to="/moderator/expenses" className="text-teal-600 hover:underline">
            ← К списку расходов
          </Link>
        </div>
      </div>
    )
  }

  const documentUrl = mediaUrl(expense.document)

  return (
    <div className="space-y-6">
      <Link to="/moderator/expenses" className="text-sm font-medium text-teal-600 hover:underline">
        ← Расходы на проверке
      </Link>
      <section className="rounded-3xl bg-white p-6 shadow-md">
        <h1 className="text-2xl font-semibold text-slate-800">Проверка расхода</h1>
        <p className="mt-2 text-sm text-slate-500">
          Карточка: {expense.card_name} · #{expense.card_id}
        </p>
        <div className="mt-4 grid gap-3 text-sm text-slate-700 sm:grid-cols-2">
          <p><span className="font-medium">Дата:</span> {formatDate(expense.date)}</p>
          <p><span className="font-medium">Сумма:</span> {formatMoney(expense.amount)}</p>
          <p><span className="font-medium">Назначение:</span> {expense.purpose}</p>
          <p><span className="font-medium">Статус:</span> {expenseStatusLabel(expense.status)}</p>
        </div>
        {expense.comment && (
          <p className="mt-4 rounded-2xl bg-sky-50 p-4 text-sm text-slate-700">
            <span className="font-medium">Комментарий автора:</span> {expense.comment}
          </p>
        )}
        {documentUrl && (
          <div className="mt-4">
            <p className="mb-2 text-sm font-medium text-slate-800">Документ</p>
            {String(expense.document || '').toLowerCase().includes('.pdf') ? (
              <iframe
                title="Документ расхода"
                src={documentUrl}
                className="h-96 w-full rounded-2xl border border-sky-100"
              />
            ) : (
              <a href={documentUrl} target="_blank" rel="noreferrer" className="text-teal-600 hover:underline">
                Открыть документ
              </a>
            )}
          </div>
        )}
      </section>
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
          <button
            type="button"
            disabled={loading}
            onClick={() => runAction('approve')}
            className="rounded-2xl bg-teal-500 px-5 py-3 text-sm font-semibold text-white disabled:opacity-60"
          >
            Одобрить
          </button>
          <button
            type="button"
            disabled={loading}
            onClick={() => runAction('clarify')}
            className="rounded-2xl bg-amber-500 px-5 py-3 text-sm font-semibold text-white disabled:opacity-60"
          >
            Запросить уточнение
          </button>
          <button
            type="button"
            disabled={loading}
            onClick={() => runAction('reject')}
            className="rounded-2xl bg-red-500 px-5 py-3 text-sm font-semibold text-white disabled:opacity-60"
          >
            Отклонить
          </button>
        </div>
      </section>
    </div>
  )
}
