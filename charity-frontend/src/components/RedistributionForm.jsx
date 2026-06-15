import { useEffect, useState } from 'react'
import { createRedistribution, fetchCards } from '../api/client'

const decisionOptions = [
  { value: 'refund', label: 'Вернуть донорам' },
  { value: 'transfer', label: 'Перераспределить на другой сбор' },
  { value: 'fund', label: 'Передать в общий фонд' },
  { value: 'hold', label: 'Оставить до завершения проверки' },
]

export default function RedistributionForm({ cardId, onSuccess }) {
  const [decisionType, setDecisionType] = useState('refund')
  const [targetCardId, setTargetCardId] = useState('')
  const [comment, setComment] = useState('')
  const [targets, setTargets] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchCards({ status: 'active' })
      .then((data) => {
        const items = (data.results || data).filter((card) => String(card.id) !== String(cardId))
        setTargets(items)
      })
      .catch(() => setTargets([]))
  }, [cardId])

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      await createRedistribution(cardId, {
        decision_type: decisionType,
        target_card_id: decisionType === 'transfer' ? Number(targetCardId) : null,
        comment,
      })
      onSuccess?.()
    } catch (err) {
      setError(err.data?.detail || 'Не удалось сохранить решение.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-3xl bg-white p-6 shadow-md">
      <h3 className="text-lg font-semibold text-slate-800">Управление распределением средств</h3>
      <p className="text-sm text-slate-500">
        Реальный возврат не выполняется — решение фиксируется в истории (демо-режим).
      </p>
      <select
        value={decisionType}
        onChange={(e) => setDecisionType(e.target.value)}
        className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm"
      >
        {decisionOptions.map((option) => (
          <option key={option.value} value={option.value}>{option.label}</option>
        ))}
      </select>
      {decisionType === 'transfer' && (
        <select
          value={targetCardId}
          onChange={(e) => setTargetCardId(e.target.value)}
          required
          className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm"
        >
          <option value="">Выберите целевой сбор</option>
          {targets.map((card) => (
            <option key={card.id} value={card.id}>{card.full_name}</option>
          ))}
        </select>
      )}
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="Комментарий"
        rows={3}
        className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm"
      />
      {error && <p className="text-sm text-red-600">{error}</p>}
      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-2xl bg-teal-500 px-6 py-3 font-semibold text-white disabled:opacity-60"
      >
        {loading ? 'Сохранение...' : 'Сохранить решение'}
      </button>
    </form>
  )
}
