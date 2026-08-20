import { useState } from 'react'
import { cancelExpense, submitExpense } from '../api/client'
import ExpenseReceiptLink from './ExpenseReceiptLink'
import { expenseCategoryLabel, expenseStatusLabel, formatDate, formatMoney } from '../utils/format'

const CAN_RESUBMIT = new Set(['draft', 'revision_required'])
const CAN_CANCEL = new Set(['draft', 'submitted', 'pending_review', 'revision_required'])

export default function ExpenseHistory({ expenses, showStatus = true, onChanged }) {
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState(null)

  if (!expenses.length) {
    return (
      <div className="rounded-3xl bg-white p-6 text-sm text-slate-500 shadow-md">
        Расходов пока нет.
      </div>
    )
  }

  async function runAction(expenseId, action) {
    setError('')
    setBusyId(expenseId)
    try {
      await action(expenseId)
      onChanged?.()
    } catch (err) {
      setError(err.data?.detail || 'Не удалось обновить расход.')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="overflow-hidden rounded-3xl bg-white p-6 shadow-md">
      <h3 className="mb-4 text-lg font-semibold text-slate-800">История расходов</h3>
      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="border-b border-sky-100 text-slate-500">
              <th className="py-2 pr-4">Дата</th>
              <th className="py-2 pr-4">Категория</th>
              <th className="py-2 pr-4">Назначение</th>
              <th className="py-2 pr-4">Сумма</th>
              {showStatus && <th className="py-2 pr-4">Статус</th>}
              <th className="py-2 pr-4">Документ</th>
              <th className="py-2">Комментарий</th>
            </tr>
          </thead>
          <tbody>
            {expenses.map((expense) => (
              <tr key={expense.id} className="border-b border-sky-50 align-top">
                <td className="py-3 pr-4">{formatDate(expense.date)}</td>
                <td className="py-3 pr-4">{expenseCategoryLabel(expense.category)}</td>
                <td className="py-3 pr-4">{expense.purpose}</td>
                <td className="py-3 pr-4">{formatMoney(expense.amount)}</td>
                {showStatus && (
                  <td className="py-3 pr-4">
                    <p>{expenseStatusLabel(expense.status)}</p>
                    {CAN_RESUBMIT.has(expense.status) && (
                      <button
                        type="button"
                        disabled={busyId === expense.id}
                        onClick={() => runAction(expense.id, submitExpense)}
                        className="mt-1 text-xs text-teal-700 hover:underline disabled:opacity-60"
                      >
                        Отправить
                      </button>
                    )}
                    {CAN_CANCEL.has(expense.status) && (
                      <button
                        type="button"
                        disabled={busyId === expense.id}
                        onClick={() => runAction(expense.id, cancelExpense)}
                        className="mt-1 block text-xs text-red-600 hover:underline disabled:opacity-60"
                      >
                        Отменить
                      </button>
                    )}
                  </td>
                )}
                <td className="py-3 pr-4">
                  <ExpenseReceiptLink expense={expense} />
                </td>
                <td className="py-3">
                  {(expense.comments || []).filter((item) => item.comment_type === 'revision_comment').map((item) => (
                    <p key={item.id}>{item.body}</p>
                  ))}
                  {!expense.comments?.length && (expense.decision_reason || expense.moderator_comment || expense.comment || '—')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
