import { Link } from 'react-router-dom'
import { mediaUrl } from '../api/client'
import { formatDate, formatMoney, statusLabel } from '../utils/format'
import ProgressBar from './ProgressBar'

export default function CardItem({ card }) {
  const photo = mediaUrl(card.photo_url)
  return (
    <article className="flex h-full flex-col overflow-hidden rounded-3xl bg-white shadow-md transition hover:-translate-y-1 hover:shadow-lg">
      <div className="aspect-[4/3] bg-sky-100">
        {photo ? (
          <img src={photo} alt={card.full_name} className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full items-center justify-center text-slate-400">Нет фото</div>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-3 p-5">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-lg font-semibold text-slate-800">{card.full_name}</h3>
          <span className="rounded-full bg-mint-100 px-3 py-1 text-xs font-medium text-teal-600">
            {statusLabel(card.status)}
          </span>
        </div>
        <p className="text-sm text-slate-600">{card.diagnosis}</p>
        <p className="text-sm text-slate-500">{card.city}{card.age ? ` · ${card.age} лет` : ''}</p>
        <div>
          <div className="mb-1 flex justify-between text-sm">
            <span className="font-medium text-slate-700">{formatMoney(card.collected_amount)}</span>
            <span className="text-slate-500">из {formatMoney(card.target_amount)}</span>
          </div>
          <ProgressBar percent={card.progress_percent} />
        </div>
        <p className="text-xs text-slate-500">До {formatDate(card.end_date)}</p>
        <div className="mt-auto flex gap-2 pt-2">
          <Link
            to={`/cards/${card.id}`}
            className="flex-1 rounded-2xl border border-sky-200 px-4 py-3 text-center text-sm font-semibold text-slate-700 transition hover:bg-sky-50"
          >
            Подробнее
          </Link>
          <Link
            to={`/cards/${card.id}#donate`}
            className="flex-1 rounded-2xl bg-teal-500 px-4 py-3 text-center text-sm font-semibold text-white transition hover:bg-teal-600"
          >
            Помочь
          </Link>
        </div>
      </div>
    </article>
  )
}
