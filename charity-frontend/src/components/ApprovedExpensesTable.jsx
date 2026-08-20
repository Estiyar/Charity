import { mediaUrl } from '../api/client'
import { expenseCategoryLabel, expenseStatusLabel, formatDate, formatMoney } from '../utils/format'

export default function ApprovedExpensesTable({ expenses = [], report }) {
  const items = report?.expenses || expenses

  return (
    <section className="rounded-3xl bg-white p-6 shadow-md">
      <h2 className="text-xl font-semibold text-slate-800">Прозрачность расходов</h2>
      <p className="mt-2 text-sm text-slate-600">
        Публично показываются подтверждённые расходы. Персональные данные и оригиналы документов скрыты.
      </p>
      {report && (
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <ReportStat label="Собрано" value={report.total_collected} />
          <ReportStat label="Подтверждённые расходы" value={report.total_confirmed_expenses} />
          <ReportStat label="На проверке" value={report.total_pending_expenses} />
          <ReportStat label="Прямые выплаты" value={report.total_direct_payouts} />
          <ReportStat label="Доступный остаток" value={report.available_balance} />
          <ReportStat label="До цели" value={report.remaining_target} />
        </div>
      )}
      {items.length ? (
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-sky-100 text-slate-500">
                <th className="py-2 pr-4">Дата</th>
                <th className="py-2 pr-4">Категория</th>
                <th className="py-2 pr-4">Назначение</th>
                <th className="py-2 pr-4">Сумма</th>
                <th className="py-2 pr-4">Статус</th>
                <th className="py-2">Документ</th>
              </tr>
            </thead>
            <tbody>
              {items.map((expense) => (
                <tr key={expense.id} className="border-b border-sky-50">
                  <td className="py-3 pr-4">{formatDate(expense.date)}</td>
                  <td className="py-3 pr-4">{expenseCategoryLabel(expense.category)}</td>
                  <td className="py-3 pr-4">{expense.purpose || '—'}</td>
                  <td className="py-3 pr-4">{formatMoney(expense.amount)}</td>
                  <td className="py-3 pr-4">
                    {expense.kind === 'payout' ? 'Прямая выплата' : expenseStatusLabel(expense.status)}
                  </td>
                  <td className="py-3">
                    {expense.public_receipt_url ? (
                      <a
                        href={mediaUrl(expense.public_receipt_url)}
                        target="_blank"
                        rel="noreferrer"
                        className="text-teal-600 hover:underline"
                      >
                        Чек
                      </a>
                    ) : (
                      '—'
                    )}
                  </td>
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

function ReportStat({ label, value }) {
  return (
    <div className="rounded-2xl bg-sky-50 p-4">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-lg font-semibold text-slate-800">{formatMoney(value)}</p>
    </div>
  )
}
