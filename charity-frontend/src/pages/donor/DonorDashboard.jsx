import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchMe, fetchMyDonations } from '../../api/client'
import { clearToken } from '../../api/auth'
import { formatDate, formatMoney, roleLabel } from '../../utils/format'

export default function DonorDashboard() {
  const [user, setUser] = useState(null)
  const [donations, setDonations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([fetchMe(), fetchMyDonations()])
      .then(([me, items]) => {
        setUser(me)
        setDonations(items)
      })
      .catch(() => setError('Не удалось загрузить данные.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-16 text-center text-slate-500">
        Загрузка...
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl space-y-8 px-4 py-10">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-800">Личный кабинет донора</h1>
          <p className="text-slate-600">Профиль и история пожертвований</p>
        </div>
        <button
          type="button"
          onClick={() => {
            clearToken()
            window.location.href = '/'
          }}
          className="rounded-2xl border border-sky-200 px-4 py-2 text-sm text-slate-600"
        >
          Выйти
        </button>
      </div>

      {error && <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>}

      {user && (
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
                  <th className="py-2">Дата</th>
                </tr>
              </thead>
              <tbody>
                {donations.map((donation) => (
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
                    <td className="py-3">{formatDate(donation.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
