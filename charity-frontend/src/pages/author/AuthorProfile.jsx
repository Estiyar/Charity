import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchMe } from '../../api/client'
import { formatDate, roleLabel } from '../../utils/format'

export default function AuthorProfile() {
  const [user, setUser] = useState(null)

  useEffect(() => {
    fetchMe().then(setUser).catch(() => setUser(null))
  }, [])

  if (!user) {
    return (
      <div className="mx-auto max-w-lg px-4 py-16 text-center text-slate-500">
        Загрузка...
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-lg space-y-6 px-4 py-10">
      <Link to="/author" className="text-sm font-medium text-teal-600 hover:underline">
        ← Личный кабинет
      </Link>
      <section className="rounded-3xl bg-white p-8 shadow-md">
        <h1 className="text-2xl font-semibold text-slate-800">Профиль</h1>
        <dl className="mt-6 space-y-4 text-sm">
          <div>
            <dt className="text-slate-500">ФИО</dt>
            <dd className="font-medium text-slate-800">{user.full_name}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Email</dt>
            <dd className="font-medium text-slate-800">{user.email}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Телефон</dt>
            <dd className="font-medium text-slate-800">{user.phone || '—'}</dd>
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
    </div>
  )
}
