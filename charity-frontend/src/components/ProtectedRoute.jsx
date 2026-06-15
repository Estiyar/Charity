import { useEffect, useState } from 'react'
import { Link, Navigate, useLocation } from 'react-router-dom'
import { fetchMe } from '../api/client'
import { getToken } from '../api/auth'

const roleLabels = {
  moderator: 'модератора',
  author: 'автора',
  donor: 'донора',
  admin: 'администратора',
}

export default function ProtectedRoute({ children, role }) {
  const location = useLocation()
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!getToken()) {
      setLoading(false)
      return
    }
    fetchMe()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="p-10 text-center text-slate-500">Загрузка...</div>
  }

  if (!user) {
    const next = encodeURIComponent(location.pathname)
    return <Navigate to={`/login?next=${next}`} replace />
  }

  if (role && user.role !== role) {
    return (
      <div className="mx-auto max-w-lg px-4 py-16 text-center">
        <div className="rounded-3xl bg-white p-8 shadow-md">
          <h1 className="text-xl font-semibold text-slate-800">Нет доступа</h1>
          <p className="mt-3 text-slate-600">
            Эта страница доступна только для {roleLabels[role] || role}.
            Вы вошли как {roleLabels[user.role] || user.role}.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <Link
              to="/login"
              className="rounded-2xl bg-teal-500 px-5 py-3 text-sm font-semibold text-white"
            >
              Войти другим аккаунтом
            </Link>
            <Link
              to="/"
              className="rounded-2xl border border-sky-200 px-5 py-3 text-sm font-semibold text-slate-600"
            >
              На главную
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return children
}
