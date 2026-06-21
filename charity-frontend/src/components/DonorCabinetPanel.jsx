import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  fetchMe,
  fetchMyBalance,
  fetchMyDonations,
  fetchMyPendingRefunds,
  fetchMyRefundHistory,
  withdrawBalance,
} from '../api/client'
import RefundDecisionForm from './RefundDecisionForm'
import {
  formatBalanceTransactionAmount,
  formatDate,
  formatDateTime,
  formatMoney,
  formatRefundOutcome,
  roleLabel,
} from '../utils/format'

function buildRefundLookup(pendingRefunds, refundHistory) {
  const lookup = new Map()
  pendingRefunds.forEach((item) => lookup.set(item.donation_id, item))
  refundHistory.forEach((item) => lookup.set(item.donation_id, item))
  return lookup
}

export default function DonorCabinetPanel({ showProfile = true }) {
  const [user, setUser] = useState(null)
  const [balanceData, setBalanceData] = useState({ balance: '0', transactions: [] })
  const [donations, setDonations] = useState([])
  const [pendingRefunds, setPendingRefunds] = useState([])
  const [refundHistory, setRefundHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [withdrawing, setWithdrawing] = useState(false)
  const [withdrawMessage, setWithdrawMessage] = useState('')
  const [error, setError] = useState('')

  const loadDashboard = useCallback(() => {
    const requests = [
      fetchMyBalance(),
      fetchMyDonations(),
      fetchMyPendingRefunds(),
      fetchMyRefundHistory(),
    ]
    if (showProfile) {
      requests.unshift(fetchMe())
    }
    return Promise.all(requests)
      .then((results) => {
        if (showProfile) {
          const [me, balance, items, pending, history] = results
          setUser(me)
          setBalanceData(balance)
          setDonations(items)
          setPendingRefunds(pending)
          setRefundHistory(history)
        } else {
          const [balance, items, pending, history] = results
          setBalanceData(balance)
          setDonations(items)
          setPendingRefunds(pending)
          setRefundHistory(history)
        }
      })
      .catch(() => setError('Не удалось загрузить данные.'))
  }, [showProfile])

  useEffect(() => {
    loadDashboard().finally(() => setLoading(false))
  }, [loadDashboard])

  const refundByDonationId = buildRefundLookup(pendingRefunds, refundHistory)
  const balanceAmount = Number(balanceData.balance || 0)

  async function handleWithdraw() {
    setWithdrawMessage('')
    setError('')
    setWithdrawing(true)
    try {
      const result = await withdrawBalance()
      setWithdrawMessage(result.message)
      await loadDashboard()
    } catch (err) {
      setError(err.data?.detail || 'Не удалось оформить вывод.')
    } finally {
      setWithdrawing(false)
    }
  }

  if (loading) {
    return (
      <div className="rounded-3xl bg-white p-8 text-center text-slate-500 shadow-md">
        Загрузка...
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {error && <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>}
      {withdrawMessage && (
        <p className="rounded-2xl bg-mint-100 px-4 py-3 text-sm text-teal-800">{withdrawMessage}</p>
      )}

      <section className="rounded-3xl bg-gradient-to-r from-teal-500 to-sky-500 p-8 text-white shadow-md">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm text-teal-50">Баланс (демо-счёт)</p>
            <p className="mt-1 text-4xl font-bold">{formatMoney(balanceData.balance)}</p>
            <p className="mt-2 text-sm text-teal-50">
              Возвраты по завершённым сборам зачисляются сюда. Реальные платежи не выполняются.
            </p>
          </div>
          <button
            type="button"
            onClick={handleWithdraw}
            disabled={withdrawing || balanceAmount <= 0}
            className="rounded-2xl bg-white px-5 py-3 text-sm font-semibold text-teal-700 hover:bg-teal-50 disabled:opacity-50"
          >
            {withdrawing ? 'Обработка...' : 'Вывести средства'}
          </button>
        </div>
      </section>

      <section className="rounded-3xl bg-white p-8 shadow-md">
        <h2 className="text-lg font-semibold text-slate-800">История баланса</h2>
        {!balanceData.transactions?.length ? (
          <p className="mt-6 text-sm text-slate-500">Операций по балансу пока нет.</p>
        ) : (
          <div className="mt-6 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-sky-100 text-slate-500">
                  <th className="py-2 pr-4">Дата</th>
                  <th className="py-2 pr-4">Операция</th>
                  <th className="py-2 pr-4">Сумма</th>
                  <th className="py-2">Комментарий</th>
                </tr>
              </thead>
              <tbody>
                {balanceData.transactions.map((item) => (
                  <tr key={item.id} className="border-b border-sky-50">
                    <td className="py-3 pr-4">{formatDateTime(item.created_at)}</td>
                    <td className="py-3 pr-4">{item.type_label}</td>
                    <td
                      className={`py-3 pr-4 font-medium ${
                        item.transaction_type === 'refund_in' ? 'text-teal-700' : 'text-red-600'
                      }`}
                    >
                      {formatBalanceTransactionAmount(item)}
                    </td>
                    <td className="py-3 text-slate-600">{item.description || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {showProfile && user && (
        <section className="rounded-3xl bg-white p-8 shadow-md">
          <h2 className="text-lg font-semibold text-slate-800">Профиль</h2>
          <dl className="mt-6 grid gap-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-slate-500">Имя</dt>
              <dd className="font-medium text-slate-800">{user.full_name}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Email</dt>
              <dd className="font-medium text-slate-800">{user.email}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Роль</dt>
              <dd className="font-medium text-slate-800">{roleLabel(user.role)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Дата регистрации</dt>
              <dd className="font-medium text-slate-800">{formatDate(user.created_at)}</dd>
            </div>
          </dl>
        </section>
      )}

      <section className="rounded-3xl bg-white p-8 shadow-md">
        <h2 className="text-lg font-semibold text-slate-800">
          Завершённые сборы — выберите, что сделать
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          Если у сбора остались неиспользованные средства, вы можете оставить их семье,
          вернуть на баланс или перенаправить на другой активный сбор.
        </p>
        {!pendingRefunds.length ? (
          <p className="mt-6 text-sm text-slate-500">Сейчас нет сборов, требующих вашего решения.</p>
        ) : (
          <div className="mt-6 space-y-4">
            {pendingRefunds.map((decision) => (
              <RefundDecisionForm
                key={decision.id}
                decision={decision}
                onResolved={loadDashboard}
              />
            ))}
          </div>
        )}
      </section>

      <section className="rounded-3xl bg-white p-8 shadow-md">
        <h2 className="text-lg font-semibold text-slate-800">История пожертвований</h2>
        {!donations.length ? (
          <p className="mt-6 text-sm text-slate-500">У вас пока нет пожертвований.</p>
        ) : (
          <div className="mt-6 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-sky-100 text-slate-500">
                  <th className="py-2 pr-4">Сбор</th>
                  <th className="py-2 pr-4">Сумма</th>
                  <th className="py-2 pr-4">Способ оплаты</th>
                  <th className="py-2 pr-4">Решение по остатку</th>
                  <th className="py-2">Дата</th>
                </tr>
              </thead>
              <tbody>
                {donations.map((donation) => {
                  const refundDecision = refundByDonationId.get(donation.id)
                  return (
                    <tr key={donation.id} className="border-b border-sky-50">
                      <td className="py-3 pr-4">
                        <Link
                          to={`/cards/${donation.card_id}`}
                          className="font-medium text-teal-600 hover:underline"
                        >
                          {donation.card_name}
                        </Link>
                      </td>
                      <td className="py-3 pr-4">{formatMoney(donation.amount)}</td>
                      <td className="py-3 pr-4">{donation.payment_method || '—'}</td>
                      <td className="py-3 pr-4 text-slate-700">
                        {refundDecision ? formatRefundOutcome(refundDecision) : '—'}
                      </td>
                      <td className="py-3">{formatDate(donation.created_at)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
