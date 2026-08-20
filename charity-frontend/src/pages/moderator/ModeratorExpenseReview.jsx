import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  approveExpense,
  fetchExpense,
  fetchExpenseOriginalBlob,
  rejectExpense,
  requestExpenseClarification,
} from '../../api/client'
import ModeratorCommentFields, { CommentHistory } from '../../components/ModeratorCommentFields'
import { expenseCategoryLabel, expenseStatusLabel, formatDate, formatMoney } from '../../utils/format'

export default function ModeratorExpenseReview() {
  const { id } = useParams()
  const [expense, setExpense] = useState(null)
  const [revisionComment, setRevisionComment] = useState('')
  const [internalComment, setInternalComment] = useState('')
  const [publishReceipt, setPublishReceipt] = useState(true)
  const [originalUrl, setOriginalUrl] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let active = true
    fetchExpense(id)
      .then((item) => {
        if (!active) return
        setExpense(item)
        setPublishReceipt(item.publish_receipt !== false)
        if (item.original_url || item.document) {
          return fetchExpenseOriginalBlob(item.id).then((url) => {
            if (active) setOriginalUrl(url)
          })
        }
        return null
      })
      .catch(() => {
        if (active) setExpense(null)
      })
    return () => {
      active = false
    }
  }, [id])

  async function runAction(action) {
    setError('')
    setLoading(true)
    try {
      const handlers = {
        approve: () => approveExpense(id, revisionComment, publishReceipt),
        reject: () => rejectExpense(id, revisionComment),
        clarify: () => requestExpenseClarification(id, revisionComment, internalComment),
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

  return (
    <div className="space-y-6">
      <Link to="/moderator/expenses" className="text-sm font-medium text-teal-600 hover:underline">
        ← Расходы на проверке
      </Link>
      <section className="rounded-3xl bg-white p-6 shadow-md">
        <h1 className="text-2xl font-semibold text-slate-800">Проверка расхода</h1>
        <p className="mt-2 text-sm text-slate-500">
          Карточка: {expense.card_name || expense.card_id} · #{expense.card_id}
        </p>
        <div className="mt-4 grid gap-3 text-sm text-slate-700 sm:grid-cols-2">
          <p><span className="font-medium">Дата:</span> {formatDate(expense.date)}</p>
          <p><span className="font-medium">Сумма:</span> {formatMoney(expense.amount)}</p>
          <p><span className="font-medium">Категория:</span> {expenseCategoryLabel(expense.category)}</p>
          <p><span className="font-medium">Назначение:</span> {expense.purpose}</p>
          <p><span className="font-medium">Статус:</span> {expenseStatusLabel(expense.status)}</p>
        </div>
        {expense.comment && (
          <p className="mt-4 rounded-2xl bg-sky-50 p-4 text-sm text-slate-700">
            <span className="font-medium">Комментарий автора:</span> {expense.comment}
          </p>
        )}
        {originalUrl && (
          <div className="mt-4">
            <p className="mb-2 text-sm font-medium text-slate-800">Оригинал документа</p>
            <iframe
              title="Документ расхода"
              src={originalUrl}
              className="h-96 w-full rounded-2xl border border-sky-100"
            />
            <a href={originalUrl} target="_blank" rel="noreferrer" className="mt-2 inline-block text-sm text-teal-600 hover:underline">
              Открыть документ
            </a>
          </div>
        )}
      </section>
      {expense.comments?.length > 0 && (
        <section className="rounded-3xl bg-white p-6 shadow-md">
          <h2 className="mb-3 text-lg font-semibold text-slate-800">История комментариев</h2>
          <CommentHistory comments={expense.comments} />
        </section>
      )}
      {expense.decisions?.length > 0 && (
        <section className="rounded-3xl bg-white p-6 shadow-md">
          <h2 className="mb-3 text-lg font-semibold text-slate-800">История решений</h2>
          <ul className="space-y-2 text-sm text-slate-700">
            {expense.decisions.map((item) => (
              <li key={item.id} className="rounded-2xl bg-sky-50 px-4 py-3">
                {item.action}
                {item.reason ? ` · ${item.reason}` : ''}
              </li>
            ))}
          </ul>
        </section>
      )}
      <section className="rounded-3xl bg-white p-6 shadow-md">
        <label className="mb-4 flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={publishReceipt}
            onChange={(e) => setPublishReceipt(e.target.checked)}
          />
          Публиковать редактированную копию чека
        </label>
        <ModeratorCommentFields
          revisionComment={revisionComment}
          onRevisionChange={setRevisionComment}
          internalComment={internalComment}
          onInternalChange={setInternalComment}
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
