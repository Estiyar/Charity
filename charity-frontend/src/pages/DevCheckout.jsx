import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { completeDevPayment, fetchPayment } from '../api/client'
import { formatMoney } from '../utils/format'

export default function DevCheckout() {
  const { paymentId } = useParams()
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [payment, setPayment] = useState(null)

  useEffect(() => {
    fetchPayment(paymentId).then(setPayment).catch(() => setError('Платёж не найден.'))
  }, [paymentId])

  async function finish(outcome) {
    setLoading(true)
    setError('')
    try {
      await completeDevPayment(paymentId, outcome)
      navigate(`/payments/result?payment=${paymentId}`)
    } catch (err) {
      setError(err.data?.detail || 'Не удалось завершить тестовую оплату.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-lg space-y-4 px-4 py-16">
      <section className="rounded-3xl bg-white p-8 shadow-md">
        <h1 className="text-2xl font-semibold text-slate-800">Тестовая оплата</h1>
        <p className="mt-2 text-sm text-slate-500">Локальный провайдер только для DEBUG/тестов.</p>
        {payment && <p className="mt-4 text-lg font-semibold">{formatMoney(payment.amount)}</p>}
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        <div className="mt-6 grid gap-3">
          <button type="button" disabled={loading} onClick={() => finish('success')} className="rounded-2xl bg-teal-500 px-5 py-3 font-semibold text-white disabled:opacity-60">
            Оплатить успешно
          </button>
          <button type="button" disabled={loading} onClick={() => finish('failed')} className="rounded-2xl border border-red-200 px-5 py-3 text-red-700 disabled:opacity-60">
            Отклонить
          </button>
          <button type="button" disabled={loading} onClick={() => finish('canceled')} className="rounded-2xl border border-sky-200 px-5 py-3 text-slate-600 disabled:opacity-60">
            Отменить
          </button>
        </div>
        <Link to="/catalog" className="mt-4 inline-block text-sm text-teal-600">К каталогу</Link>
      </section>
    </div>
  )
}
