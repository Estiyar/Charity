import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchRedistributionCards } from '../../api/client'
import { formatMoney, redistributionCaseLabel, statusLabel } from '../../utils/format'

export default function ModeratorRedistribution() {
  const [cards, setCards] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchRedistributionCards()
      .then(setCards)
      .catch(() => setCards([]))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="rounded-3xl bg-white p-8 text-slate-500 shadow-md">Загрузка...</div>
  }

  return (
    <section className="rounded-3xl bg-white p-6 shadow-md">
      <h1 className="mb-6 text-2xl font-semibold text-slate-800">Перераспределение средств</h1>
      {!cards.length ? (
        <p className="text-slate-500">Карточек для перераспределения нет.</p>
      ) : (
        <div className="space-y-3">
          {cards.map((card) => (
            <div key={card.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-sky-50 p-4">
              <div>
                <p className="font-medium text-slate-800">{card.full_name}</p>
                <p className="text-sm text-slate-500">
                  {statusLabel(card.status)} · Остаток {formatMoney(card.escrow_balance)}
                </p>
                <p className="text-xs text-slate-400">
                  {redistributionCaseLabel(card.redistribution_case)}
                </p>
              </div>
              <Link
                to={`/moderator/cards/${card.id}`}
                className="rounded-2xl bg-teal-500 px-4 py-2 text-sm font-semibold text-white"
              >
                Управлять
              </Link>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
