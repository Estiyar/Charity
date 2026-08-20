import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { fetchPayment } from '../api/client'
import { formatMoney, paymentStatusLabel } from '../utils/format'

export default function PaymentResult() {
  const [params] = useSearchParams()
  const paymentId = params.get('payment')
  const [payment, setPayment] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!paymentId) {
      setError('Платёж не указан.')
      setLoading(false)
      return
    }
    let cancelled = false
    function load() {
      fetchPayment(paymentId)
        .then((data) => {
          if (cancelled) return
          setPayment(data)
          setError('')
        })
        .catch(() => {
          if (!cancelled) setError('Не удалось получить статус оплаты.')
        })
        .finally(() => {
          if (!cancelled) setLoading(false)
        })
    }
    load()
    const timer = setInterval(load, 2000)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [paymentId])

  if (loading) {
    return <div className="mx-auto max-w-lg px-4 py-16 text-center text-slate-500">Проверяем оплату...</div>
  }

  if (error && !payment) {
    return (
      <div className="mx-auto max-w-lg px-4 py-16 text-center">
        <p className="text-slate-600">{error}</p>
        <Link to="/catalog" className="mt-4 inline-block text-teal-600">К каталогу</Link>
      </div>
    )
  }

  const status = payment?.payment_status
  const isSuccess = status === 'success'
  const isPending = status === 'pending' || status === 'processing'

  return (
    <div className="mx-auto max-w-lg space-y-4 px-4 py-16">
      <section className="rounded-3xl bg-white p-8 shadow-md">
        <h1 className="text-2xl font-semibold text-slate-800">
          {isSuccess ? 'Спасибо за помощь' : isPending ? 'Оплата обрабатывается' : 'Оплата не завершена'}
        </h1>
        <p className="mt-3 text-sm text-slate-600">Статус: {paymentStatusLabel(status)}</p>
        {payment?.amount && <p className="mt-2 text-lg font-semibold text-slate-800">{formatMoney(payment.amount)}</p>}
        {payment?.failed_reason && <p className="mt-3 text-sm text-red-600">{payment.failed_reason}</p>}
        {isPending && <p className="mt-3 text-sm text-slate-500">Страница обновится после подтверждения провайдера.</p>}
        <Link
          to={payment?.card_id ? `/cards/${payment.card_id}` : '/catalog'}
          className="mt-6 inline-block rounded-2xl bg-teal-500 px-5 py-3 text-sm font-semibold text-white"
        >
          Вернуться к сбору
        </Link>
      </section>
    </div>
  )
}
