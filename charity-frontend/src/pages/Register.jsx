import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { login, parseApiError, register } from '../api/client'

const initialForm = {
  full_name: '',
  email: '',
  phone: '',
  password: '',
  repeat_password: '',
  role: 'donor',
  personal_data_consent: false,
}

export default function Register() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [form, setForm] = useState(initialForm)

  useEffect(() => {
    const role = searchParams.get('role')
    if (role === 'author' || role === 'donor') {
      setForm((prev) => ({ ...prev, role }))
    }
  }, [searchParams])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    if (!form.personal_data_consent) {
      setError('Необходимо согласие на обработку персональных данных.')
      return
    }
    setLoading(true)
    try {
      await register({
        full_name: form.full_name,
        email: form.email,
        phone: form.phone,
        password: form.password,
        repeat_password: form.repeat_password,
        role: form.role,
      })
      await login(form.email, form.password)
      navigate(form.role === 'author' ? '/author' : '/')
    } catch (err) {
      if (!err.data && !err.status) {
        setError('Сервер недоступен. Запустите backend: python manage.py runserver')
        return
      }
      setError(parseApiError(err.data, 'Не удалось зарегистрироваться.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-lg px-4 py-16">
      <form onSubmit={handleSubmit} className="space-y-4 rounded-3xl bg-white p-8 shadow-md">
        <h1 className="text-2xl font-semibold text-slate-800">Регистрация</h1>
        <input
          type="text"
          placeholder="ФИО"
          value={form.full_name}
          onChange={(e) => updateField('full_name', e.target.value)}
          required
          className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
        />
        <input
          type="email"
          placeholder="Email"
          value={form.email}
          onChange={(e) => updateField('email', e.target.value)}
          required
          className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
        />
        <input
          type="text"
          placeholder="Телефон"
          value={form.phone}
          onChange={(e) => updateField('phone', e.target.value)}
          className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
        />
        <select
          value={form.role}
          onChange={(e) => updateField('role', e.target.value)}
          className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
        >
          <option value="donor">Донор</option>
          <option value="author">Автор сбора</option>
        </select>
        <input
          type="password"
          placeholder="Пароль"
          value={form.password}
          onChange={(e) => updateField('password', e.target.value)}
          required
          minLength={8}
          className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
        />
        <p className="text-xs text-slate-500">Минимум 8 символов</p>
        <input
          type="password"
          placeholder="Повторите пароль"
          value={form.repeat_password}
          onChange={(e) => updateField('repeat_password', e.target.value)}
          required
          className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
        />
        <label className="flex items-start gap-3 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={form.personal_data_consent}
            onChange={(e) => updateField('personal_data_consent', e.target.checked)}
            className="mt-1"
          />
          <span>Согласен(на) на обработку персональных данных</span>
        </label>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-2xl bg-teal-500 px-6 py-4 font-semibold text-white hover:bg-teal-600 disabled:opacity-60"
        >
          {loading ? 'Регистрация...' : 'Зарегистрироваться'}
        </button>
        <p className="text-center text-sm text-slate-600">
          Уже есть аккаунт?{' '}
          <Link to="/login" className="font-medium text-teal-600 hover:underline">
            Войти
          </Link>
        </p>
      </form>
    </div>
  )
}
