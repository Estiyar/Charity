import { useEffect, useState } from 'react'
import { changeCardStatus, fetchAdminCards } from '../../api/client'
import { formatDate, formatMoney, statusLabel } from '../../utils/format'

const statuses = [
  'draft', 'pending_moderation', 'revision_required', 'approved', 'active',
  'rejected', 'completed', 'deceased', 'redistribution', 'archived',
]

export default function AdminCards() {
  const [cards, setCards] = useState([])
  const [loading, setLoading] = useState(true)

  function load() {
    setLoading(true)
    fetchAdminCards().then(setCards).finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  async function handleStatusChange(cardId, status) {
    await changeCardStatus(cardId, status)
    load()
  }

  if (loading) {
    return <div className="rounded-3xl bg-white p-8 text-slate-500 shadow-md">Загрузка...</div>
  }

  return (
    <section className="rounded-3xl bg-white p-6 shadow-md">
      <h1 className="mb-6 text-2xl font-semibold text-slate-800">Карточки</h1>
      <div className="space-y-3">
        {cards.map((card) => (
          <div key={card.id} className="rounded-2xl bg-sky-50 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-medium text-slate-800">{card.full_name}</p>
                <p className="text-sm text-slate-500">
                  {card.author_name} · {statusLabel(card.status)} · {formatMoney(card.collected_amount)}
                </p>
                <p className="text-xs text-slate-400">До {formatDate(card.end_date)}</p>
              </div>
              <select
                value={card.status}
                onChange={(e) => handleStatusChange(card.id, e.target.value)}
                className="rounded-xl border border-sky-100 px-3 py-2 text-sm"
              >
                {statuses.map((status) => (
                  <option key={status} value={status}>{statusLabel(status)}</option>
                ))}
              </select>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
