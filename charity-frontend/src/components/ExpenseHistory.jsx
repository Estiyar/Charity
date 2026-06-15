import { mediaUrl } from '../api/client'
import { expenseStatusLabel, formatDate, formatMoney } from '../utils/format'

export default function ExpenseHistory({ expenses, showStatus = true }) {
  if (!expenses.length) {
    return (
      <div className="rounded-3xl bg-white p-6 text-sm text-slate-500 shadow-md">
        Расходов пока нет.
      </div>
    )
  }

  return (
    <div className="overflow-hidden rounded-3xl bg-white p-6 shadow-md">
      <h3 className="mb-4 text-lg font-semibold text-slate-800">История расходов</h3>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="border-b border-sky-100 text-slate-500">
              <th className="py-2 pr-4">Дата</th>
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
                <td className="py-3 pr-4">{expense.purpose}</td>
                <td className="py-3 pr-4">{formatMoney(expense.amount)}</td>
                {showStatus && (
                  <td className="py-3 pr-4">{expenseStatusLabel(expense.status)}</td>
                )}
                <td className="py-3 pr-4">
                  {expense.document ? (
                    <a
                      href={mediaUrl(expense.document)}
                      target="_blank"
                      rel="noreferrer"
                      className="text-teal-600 hover:underline"
                    >
                      Открыть
                    </a>
                  ) : (
                    '—'
                  )}
                </td>
                <td className="py-3">
                  {expense.comment || expense.moderator_comment || '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
