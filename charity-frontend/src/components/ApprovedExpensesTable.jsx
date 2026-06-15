import { mediaUrl } from '../api/client'
import { expenseStatusLabel, formatDate, formatMoney } from '../utils/format'

export default function ApprovedExpensesTable({ expenses }) {
  return (
    <section className="rounded-3xl bg-white p-6 shadow-md">
      <h2 className="text-xl font-semibold text-slate-800">Подтверждённые расходы</h2>
      <p className="mt-2 text-sm text-slate-600">
        Публично отображаются только одобренные расходы.
      </p>
      {expenses.length ? (
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-sky-100 text-slate-500">
                <th className="py-2 pr-4">Дата</th>
                <th className="py-2 pr-4">Назначение</th>
                <th className="py-2 pr-4">Сумма</th>
                <th className="py-2 pr-4">Статус</th>
                <th className="py-2 pr-4">Документ</th>
                <th className="py-2">Комментарий</th>
              </tr>
            </thead>
            <tbody>
              {expenses.map((expense) => (
                <tr key={expense.id} className="border-b border-sky-50">
                  <td className="py-3 pr-4">{formatDate(expense.date)}</td>
                  <td className="py-3 pr-4">{expense.purpose}</td>
                  <td className="py-3 pr-4">{formatMoney(expense.amount)}</td>
                  <td className="py-3 pr-4">{expenseStatusLabel(expense.status)}</td>
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
                  <td className="py-3">{expense.comment || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="mt-4 text-sm text-slate-500">Подтверждённых расходов пока нет.</p>
      )}
    </section>
  )
}
