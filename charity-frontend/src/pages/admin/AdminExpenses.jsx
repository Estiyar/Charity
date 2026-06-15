import { useEffect, useState } from 'react'
import { fetchAdminExpenses } from '../../api/client'
import { expenseStatusLabel, formatDate, formatMoney } from '../../utils/format'

export default function AdminExpenses() {
  const [expenses, setExpenses] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAdminExpenses()
      .then(setExpenses)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="rounded-3xl bg-white p-8 text-slate-500 shadow-md">Загрузка...</div>
  }

  return (
    <section className="rounded-3xl bg-white p-6 shadow-md">
      <h1 className="mb-6 text-2xl font-semibold text-slate-800">Расходы</h1>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="border-b border-sky-100 text-slate-500">
              <th className="py-2 pr-4">Сбор</th>
              <th className="py-2 pr-4">Назначение</th>
              <th className="py-2 pr-4">Сумма</th>
              <th className="py-2 pr-4">Статус</th>
              <th className="py-2">Дата</th>
            </tr>
          </thead>
          <tbody>
            {expenses.map((expense) => (
              <tr key={expense.id} className="border-b border-sky-50">
                <td className="py-3 pr-4">{expense.card_name}</td>
                <td className="py-3 pr-4">{expense.purpose}</td>
                <td className="py-3 pr-4">{formatMoney(expense.amount)}</td>
                <td className="py-3 pr-4">{expenseStatusLabel(expense.status)}</td>
                <td className="py-3">{formatDate(expense.date)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
