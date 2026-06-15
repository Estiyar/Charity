import { useEffect, useState } from 'react'
import { fetchAdminModerators } from '../../api/client'

export default function AdminModerators() {
  const [moderators, setModerators] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAdminModerators()
      .then(setModerators)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="rounded-3xl bg-white p-8 text-slate-500 shadow-md">Загрузка...</div>
  }

  return (
    <section className="rounded-3xl bg-white p-6 shadow-md">
      <h1 className="mb-6 text-2xl font-semibold text-slate-800">Модераторы</h1>
      <div className="space-y-3">
        {moderators.map((moderator) => (
          <div key={moderator.id} className="rounded-2xl bg-sky-50 p-4">
            <p className="font-medium text-slate-800">{moderator.full_name}</p>
            <p className="text-sm text-slate-500">{moderator.email} · {moderator.status}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
