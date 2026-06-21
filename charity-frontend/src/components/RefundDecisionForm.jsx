import { useState } from 'react'
import { Link } from 'react-router-dom'
import { chooseRefundDecision } from '../api/client'
import { formatDateTime, formatMoney } from '../utils/format'

function formatRedirectOptionLabel(card) {
  return `${card.full_name} — ${card.diagnosis}, ${card.city} (${formatMoney(card.collected_amount)} / ${formatMoney(card.target_amount)})`
}

export default function RefundDecisionForm({ decision, onResolved }) {
  const [choice, setChoice] = useState('')
  const [targetCardId, setTargetCardId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const redirectOptions = decision.redirect_options || []
  const canSubmitRedirect = choice !== 'redirect' || targetCardId

  async function handleSubmit(event) {
    event.preventDefault()
    if (!choice) {
      setError('Выберите один из вариантов.')
      return
    }
    if (choice === 'redirect' && !targetCardId) {
      setError('Выберите целевой сбор.')
      return
    }
    setError('')
    setLoading(true)
    try {
      const payload = { choice }
      if (choice === 'redirect') {
        payload.target_card_id = Number(targetCardId)
      }
      await chooseRefundDecision(decision.id, payload)
      onResolved?.()
    } catch (err) {
      setError(
        err.data?.choice?.[0]
          || err.data?.target_card_id?.[0]
          || err.data?.detail
          || 'Не удалось сохранить решение.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-2xl border border-purple-100 bg-purple-50/40 p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold text-slate-800">{decision.card.full_name}</h3>
          <p className="text-sm text-slate-600">
            {decision.card.diagnosis} · {decision.card.city}
          </p>
        </div>
        <div className="text-right">
          <p className="text-sm text-slate-500">Ваша доля остатка</p>
          <p className="text-lg font-semibold text-purple-800">{formatMoney(decision.share_amount)}</p>
        </div>
      </div>

      <p className="mb-4 text-sm text-slate-600">
        Срок решения: {formatDateTime(decision.deadline)}
      </p>

      <fieldset className="space-y-3">
        {(decision.options || []).map((option) => (
          <label
            key={option.value}
            className={`flex cursor-pointer items-start gap-3 rounded-xl border px-4 py-3 transition ${
              choice === option.value
                ? 'border-teal-400 bg-white'
                : 'border-sky-100 bg-white/70 hover:border-sky-200'
            }`}
          >
            <input
              type="radio"
              name={`refund-choice-${decision.id}`}
              value={option.value}
              checked={choice === option.value}
              onChange={() => {
                setChoice(option.value)
                setError('')
                if (option.value !== 'redirect') {
                  setTargetCardId('')
                }
              }}
              className="mt-1"
            />
            <span>
              <span className="block font-medium text-slate-800">{option.label}</span>
              {option.value === 'refund' && decision.refund_payout && (
                <span className="mt-1 block text-sm text-slate-500">
                  К выплате {formatMoney(decision.refund_payout.net_amount)}
                  {' '}
                  (комиссия {decision.refund_payout.commission_percent}%)
                </span>
              )}
            </span>
          </label>
        ))}
      </fieldset>

      {choice === 'redirect' && (
        <div className="mt-4">
          <label className="mb-2 block text-sm font-medium text-slate-700">
            Целевой сбор
          </label>
          <select
            value={targetCardId}
            onChange={(event) => setTargetCardId(event.target.value)}
            className="w-full rounded-xl border border-sky-100 bg-white px-4 py-3 text-sm outline-none focus:border-teal-500"
          >
            <option value="">Выберите сбор</option>
            {redirectOptions.map((card) => (
              <option key={card.id} value={card.id}>
                {formatRedirectOptionLabel(card)}
              </option>
            ))}
          </select>
        </div>
      )}

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={loading || !canSubmitRedirect}
          className="rounded-2xl bg-teal-500 px-5 py-3 text-sm font-semibold text-white hover:bg-teal-600 disabled:opacity-50"
        >
          {loading ? 'Сохранение...' : 'Подтвердить решение'}
        </button>
        <Link
          to={`/cards/${decision.card.id}`}
          className="text-sm font-medium text-teal-600 hover:underline"
        >
          Открыть сбор
        </Link>
      </div>
    </form>
  )
}
