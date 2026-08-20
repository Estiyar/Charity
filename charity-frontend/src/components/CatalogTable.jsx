import { Link } from 'react-router-dom'
import { formatDate, formatMoney, statusBadgeClass, statusLabel } from '../utils/format'
import ProgressBar from './ProgressBar'

export default function CatalogTable({ cards = [], emptyMessage = 'Сборы не найдены' }) {
  if (!cards.length) {
    return (
      <div className="rounded-3xl bg-white p-10 text-center text-slate-500 shadow-md">
        {emptyMessage}
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-3xl bg-white shadow-md">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-sky-50 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-4 py-3 font-semibold">Получатель</th>
            <th className="hidden px-4 py-3 font-semibold md:table-cell">Диагноз</th>
            <th className="hidden px-4 py-3 font-semibold sm:table-cell">Город</th>
            <th className="hidden px-4 py-3 font-semibold lg:table-cell">Возраст</th>
            <th className="px-4 py-3 font-semibold">Собрано</th>
            <th className="hidden px-4 py-3 font-semibold xl:table-cell">Прогресс</th>
            <th className="hidden px-4 py-3 font-semibold lg:table-cell">Окончание</th>
            <th className="px-4 py-3 font-semibold">Статус</th>
            <th className="px-4 py-3 font-semibold" />
          </tr>
        </thead>
        <tbody>
          {cards.map((card) => (
            <tr key={card.id} className="border-t border-sky-50">
              <td className="px-4 py-3 font-medium text-slate-800">{card.full_name}</td>
              <td className="hidden px-4 py-3 text-slate-600 md:table-cell">{card.diagnosis}</td>
              <td className="hidden px-4 py-3 text-slate-600 sm:table-cell">{card.city}</td>
              <td className="hidden px-4 py-3 text-slate-600 lg:table-cell">{card.age ?? '—'}</td>
              <td className="px-4 py-3 text-slate-700">
                {formatMoney(card.collected_amount)} / {formatMoney(card.target_amount)}
              </td>
              <td className="hidden min-w-[140px] px-4 py-3 xl:table-cell">
                <ProgressBar percent={card.progress_percent} />
              </td>
              <td className="hidden px-4 py-3 text-slate-500 lg:table-cell">{formatDate(card.end_date)}</td>
              <td className="px-4 py-3">
                <span className={`rounded-full px-3 py-1 text-xs font-medium ${statusBadgeClass(card.status)}`}>
                  {statusLabel(card.status)}
                </span>
              </td>
              <td className="px-4 py-3 text-right">
                <Link to={`/cards/${card.id}`} className="font-semibold text-teal-600 hover:underline">
                  Открыть
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
