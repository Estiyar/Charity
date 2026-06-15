import { useEffect, useState } from 'react'
import { fetchAdminDonations } from '../../api/client'
import { formatDate, formatMoney } from '../../utils/format'

export default function AdminDonations() {
  const [donations, setDonations] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAdminDonations()
      .then(setDonations)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="rounded-3xl bg-white p-8 text-slate-500 shadow-md">Загрузка...</div>
  }

  return (
    <section className="rounded-3xl bg-white p-6 shadow-md">
      <h1 className="mb-6 text-2xl font-semibold text-slate-800">Пожертвования</h1>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="border-b border-sky-100 text-slate-500">
              <th className="py-2 pr-4">Сбор</th>
              <th className="py-2 pr-4">Донор</th>
              <th className="py-2 pr-4">Сумма</th>
              <th className="py-2">Дата</th>
            </tr>
          </thead>
          <tbody>
            {donations.map((donation) => (
              <tr key={donation.id} className="border-b border-sky-50">
                <td className="py-3 pr-4">{donation.card_name}</td>
                <td className="py-3 pr-4">{donation.donor_name}</td>
                <td className="py-3 pr-4">{formatMoney(donation.amount)}</td>
                <td className="py-3">{formatDate(donation.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
