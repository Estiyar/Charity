import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchExpenses, fetchMyCards, submitCard } from '../../api/client'
import EscrowBlock from '../../components/EscrowBlock'
import ExpenseForm from '../../components/ExpenseForm'
import ExpenseHistory from '../../components/ExpenseHistory'
import { formatDate, formatMoney, statusBadgeClass, statusLabel } from '../../utils/format'

const EXPENSE_CARD_STATUSES = new Set(['active', 'completed'])
const REVISION_STATUSES = new Set(['revision_required'])
const REJECTED_STATUSES = new Set(['rejected'])

function SectionTitle({ children }) {
  return <h2 className="text-lg font-semibold text-slate-800">{children}</h2>
}

function CardArticle({ card, onSubmit }) {
  const showModeratorComment = (
    card.moderator_comment
    && (REVISION_STATUSES.has(card.status) || REJECTED_STATUSES.has(card.status))
  )

  return (
    <article className="rounded-3xl bg-white p-6 shadow-md">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-xl font-semibold text-slate-800">{card.full_name}</h3>
            <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(card.status)}`}>
              {statusLabel(card.status)}
            </span>
          </div>
          <p className="text-sm text-slate-500">{card.diagnosis} · {card.city}</p>
          <p className="text-sm text-slate-600">
            Цель {formatMoney(card.target_amount)} · Собрано {formatMoney(card.collected_amount)}
          </p>
          <p className="text-sm text-slate-500">До {formatDate(card.end_date)}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {card.status === 'draft' && (
            <button
              type="button"
              onClick={() => onSubmit(card.id)}
              className="rounded-2xl bg-amber-500 px-4 py-2 text-sm font-semibold text-white"
            >
              На модерацию
            </button>
          )}
          <Link
            to={`/cards/${card.id}`}
            className="rounded-2xl bg-teal-500 px-4 py-2 text-sm font-semibold text-white"
          >
            Открыть
          </Link>
        </div>
      </div>
      {showModeratorComment && (
        <div className="mt-4 rounded-2xl bg-amber-50 p-4 text-sm text-slate-700">
          <p className="font-medium text-slate-800">Комментарий модератора</p>
          <p>{card.moderator_comment}</p>
        </div>
      )}
    </article>
  )
}

export default function AuthorFundraisers() {
  const [cards, setCards] = useState([])
  const [expensesByCard, setExpensesByCard] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadExpenses = useCallback((cardId) => {
    fetchExpenses(cardId)
      .then((items) => setExpensesByCard((prev) => ({ ...prev, [cardId]: items })))
      .catch(() => setExpensesByCard((prev) => ({ ...prev, [cardId]: [] })))
  }, [])

  const loadCards = useCallback(() => {
    setLoading(true)
    setError('')
    fetchMyCards()
      .then((items) => {
        setCards(items)
        items.forEach((card) => {
          if (EXPENSE_CARD_STATUSES.has(card.status)) {
            loadExpenses(card.id)
          }
        })
      })
      .catch(() => {
        setCards([])
        setError('Не удалось загрузить карточки.')
      })
      .finally(() => setLoading(false))
  }, [loadExpenses])

  useEffect(() => {
    loadCards()
  }, [loadCards])

  const pendingModerationCards = cards.filter((card) => card.status === 'pending_moderation')
  const revisionRequiredCards = cards.filter((card) => card.status === 'revision_required')
  const myCards = cards.filter(
    (card) => card.status !== 'pending_moderation' && card.status !== 'revision_required',
  )
  const expenseCards = cards.filter((card) => EXPENSE_CARD_STATUSES.has(card.status))

  async function handleSubmit(cardId) {
    try {
      await submitCard(cardId)
      loadCards()
    } catch {
      setError('Не удалось отправить карточку на модерацию.')
    }
  }

  function refreshCard(cardId) {
    loadExpenses(cardId)
    loadCards()
  }

  if (error) {
    return <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>
  }

  if (loading) {
    return (
      <div className="rounded-3xl bg-white p-8 text-center text-slate-500 shadow-md">
        Загрузка...
      </div>
    )
  }

  if (!cards.length) {
    return (
      <div className="rounded-3xl bg-white p-8 text-center text-slate-500 shadow-md">
        <p>У вас пока нет карточек.</p>
        <Link to="/author/create" className="mt-4 inline-block text-teal-600 hover:underline">
          Создать первый сбор
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {pendingModerationCards.length > 0 && (
        <section className="space-y-4">
          <SectionTitle>Заявки на модерации</SectionTitle>
          <div className="space-y-4">
            {pendingModerationCards.map((card) => (
              <CardArticle key={card.id} card={card} onSubmit={handleSubmit} />
            ))}
          </div>
        </section>
      )}

      {revisionRequiredCards.length > 0 && (
        <section className="space-y-4">
          <SectionTitle>Требуют доработки</SectionTitle>
          <div className="space-y-4">
            {revisionRequiredCards.map((card) => (
              <CardArticle key={card.id} card={card} onSubmit={handleSubmit} />
            ))}
          </div>
        </section>
      )}

      {myCards.length > 0 && (
        <section className="space-y-4">
          <SectionTitle>Мои сборы</SectionTitle>
          <div className="space-y-4">
            {myCards.map((card) => (
              <CardArticle key={card.id} card={card} onSubmit={handleSubmit} />
            ))}
          </div>
        </section>
      )}

      {expenseCards.length > 0 && (
        <section className="space-y-6">
          <SectionTitle>История расходов</SectionTitle>
          {expenseCards.map((card) => (
            <div key={`exp-${card.id}`} className="space-y-4">
              <EscrowBlock card={card} />
              <div className="grid gap-6 lg:grid-cols-2">
                <ExpenseForm cardId={card.id} onSuccess={() => refreshCard(card.id)} />
                <ExpenseHistory expenses={expensesByCard[card.id] || []} />
              </div>
            </div>
          ))}
        </section>
      )}
    </div>
  )
}
