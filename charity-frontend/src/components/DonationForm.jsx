import { useState } from 'react'
import { donate } from '../api/client'
import { formatMoney } from '../utils/format'

const QUICK_AMOUNTS = [1000, 5000, 10000, 20000]

const PAYMENT_METHODS = [
  { value: 'card', label: 'Банковская карта' },
  { value: 'transfer', label: 'Перевод' },
  { value: 'wallet', label: 'Электронный кошелёк' },
]

export default function DonationForm({ cardId, onSuccess }) {
  const [amountChoice, setAmountChoice] = useState(5000)
  const [customAmount, setCustomAmount] = useState('')
  const [donorName, setDonorName] = useState('')
  const [contact, setContact] = useState('')
  const [paymentMethod, setPaymentMethod] = useState('card')
  const [consent, setConsent] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [isOther, setIsOther] = useState(false)

  const resolvedAmount = isOther ? Number(customAmount) : amountChoice

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSuccessMessage('')
    if (!consent) {
      setError('Необходимо согласие на обработку персональных данных.')
      return
    }
    if (!resolvedAmount || resolvedAmount <= 0) {
      setError('Укажите корректную сумму пожертвования.')
      return
    }
    setLoading(true)
    try {
      const result = await donate(cardId, {
        amount: resolvedAmount.toFixed(2),
        donor_name: donorName,
        contact,
        payment_method: paymentMethod,
        personal_data_consent: true,
      })
      setSuccessMessage(result.message)
      onSuccess?.(result)
    } catch (err) {
      const message = err.data?.amount?.[0]
        || err.data?.personal_data_consent?.[0]
        || err.data?.non_field_errors?.[0]
        || (typeof err.data?.detail === 'string' ? err.data.detail : null)
        || 'Не удалось выполнить пожертвование.'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5 rounded-3xl bg-white p-6 shadow-md">
      <h3 className="text-xl font-semibold text-slate-800">Сделать пожертвование</h3>
      <div>
        <p className="mb-3 text-sm font-medium text-slate-700">Быстрый выбор суммы</p>
        <div className="flex flex-wrap gap-2">
          {QUICK_AMOUNTS.map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => {
                setIsOther(false)
                setAmountChoice(value)
              }}
              className={`rounded-2xl px-4 py-3 text-sm font-semibold transition ${
                !isOther && amountChoice === value
                  ? 'bg-teal-500 text-white'
                  : 'bg-sky-100 text-slate-700 hover:bg-sky-200'
              }`}
            >
              {formatMoney(value)}
            </button>
          ))}
          <button
            type="button"
            onClick={() => setIsOther(true)}
            className={`rounded-2xl px-4 py-3 text-sm font-semibold transition ${
              isOther ? 'bg-teal-500 text-white' : 'bg-sky-100 text-slate-700 hover:bg-sky-200'
            }`}
          >
            Другая
          </button>
        </div>
        {isOther && (
          <input
            type="number"
            min="1"
            placeholder="Введите сумму"
            value={customAmount}
            onChange={(e) => setCustomAmount(e.target.value)}
            className="mt-3 w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
          />
        )}
      </div>
      <input
        type="text"
        placeholder="Ваше имя"
        value={donorName}
        onChange={(e) => setDonorName(e.target.value)}
        required
        className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
      />
      <input
        type="text"
        placeholder="Телефон или email"
        value={contact}
        onChange={(e) => setContact(e.target.value)}
        required
        className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
      />
      <select
        value={paymentMethod}
        onChange={(e) => setPaymentMethod(e.target.value)}
        className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
      >
        {PAYMENT_METHODS.map((method) => (
          <option key={method.value} value={method.value}>{method.label}</option>
        ))}
      </select>
      <label className="flex items-start gap-3 text-sm text-slate-600">
        <input
          type="checkbox"
          checked={consent}
          onChange={(e) => setConsent(e.target.checked)}
          className="mt-1"
        />
        <span>Согласен(на) на обработку персональных данных</span>
      </label>
      {error && <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>}
      {successMessage && (
        <p className="rounded-2xl bg-mint-100 px-4 py-3 text-sm text-teal-700">{successMessage}</p>
      )}
      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-2xl bg-teal-500 px-6 py-4 text-base font-semibold text-white shadow-md transition hover:bg-teal-600 disabled:opacity-60"
      >
        {loading ? 'Обработка...' : 'Пожертвовать'}
      </button>
    </form>
  )
}
