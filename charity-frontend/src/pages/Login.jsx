import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { fetchMe, login, parseApiError } from '../api/client'

const roleHome = {
  moderator: '/moderator',
  author: '/author',
  admin: '/admin',
  donor: '/',
}

export default function Login() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const nextPath = searchParams.get('next')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      const user = await fetchMe()
      const destination = nextPath || roleHome[user.role] || '/'
      navigate(destination)
    } catch (err) {
      if (!err.data && !err.status) {
        setError('Сервер недоступен. Запустите backend: python manage.py runserver')
        return
      }
      setError(parseApiError(err.data, 'Неверный email или пароль'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-md px-4 py-16">
      <form onSubmit={handleSubmit} className="space-y-4 rounded-3xl bg-white p-8 shadow-md">
        <h1 className="text-2xl font-semibold text-slate-800">Вход</h1>
        {nextPath && (
          <p className="rounded-2xl bg-sky-50 px-4 py-3 text-sm text-slate-600">
            Войдите, чтобы открыть запрошенную страницу.
          </p>
        )}
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
        />
        <input
          type="password"
          placeholder="Пароль"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-2xl bg-teal-500 px-6 py-4 font-semibold text-white hover:bg-teal-600 disabled:opacity-60"
        >
          {loading ? 'Вход...' : 'Войти'}
        </button>
        <p className="text-center text-sm text-slate-600">
          Нет аккаунта?{' '}
          <Link to="/register" className="font-medium text-teal-600 hover:underline">
            Зарегистрироваться
          </Link>
        </p>
      </form>
    </div>
  )
}
