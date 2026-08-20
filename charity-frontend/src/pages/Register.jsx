import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { login, parseApiError, parseApiFieldErrors, registerWithEcp, requestEcpChallenge, verifyEcpSignature } from '../api/client'
import { buildDevCms, isDevEcpEnabled, signChallengeWithNcaLayer } from '../api/ncalayer'
import PasswordInput from '../components/PasswordInput'

const initialForm = {
  email: '',
  phone: '',
  password: '',
  repeat_password: '',
  role: 'donor',
  personal_data_consent: false,
}

function fieldClassName(hasError) {
  return `w-full rounded-2xl border px-4 py-3 text-sm outline-none focus:border-teal-500 ${
    hasError ? 'border-red-300 focus:border-red-400' : 'border-sky-100'
  }`
}

function passwordFieldClassName(hasError) {
  return `w-full rounded-2xl border px-4 py-3 pr-12 text-sm outline-none focus:border-teal-500 ${
    hasError ? 'border-red-300 focus:border-red-400' : 'border-sky-100'
  }`
}

function FieldError({ message }) {
  if (!message) return null
  return <p className="text-xs text-red-600">{message}</p>
}

export default function Register() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [form, setForm] = useState(initialForm)
  const [ecpProfile, setEcpProfile] = useState(null)
  const [ecpSessionToken, setEcpSessionToken] = useState('')
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [signing, setSigning] = useState(false)

  useEffect(() => {
    const role = searchParams.get('role')
    if (role === 'author' || role === 'donor') {
      setForm((prev) => ({ ...prev, role }))
    }
  }, [searchParams])

  function clearFieldError(field) {
    setFieldErrors((prev) => {
      if (!prev[field]) return prev
      const next = { ...prev }
      delete next[field]
      return next
    })
  }

  function updateField(field, value) {
    clearFieldError(field)
    setError('')
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function completeEcp(cms) {
    const challenge = await requestEcpChallenge()
    const verified = await verifyEcpSignature({
      challenge_id: challenge.challenge_id,
      cms: typeof cms === 'function' ? cms(challenge.challenge) : cms,
    })
    setEcpSessionToken(verified.ecp_session_token)
    setEcpProfile(verified)
  }

  async function handleNcaLayerSign() {
    setError('')
    setSigning(true)
    try {
      const challenge = await requestEcpChallenge()
      const cms = await signChallengeWithNcaLayer(challenge.challenge)
      const verified = await verifyEcpSignature({
        challenge_id: challenge.challenge_id,
        cms,
      })
      setEcpSessionToken(verified.ecp_session_token)
      setEcpProfile(verified)
    } catch (err) {
      setError(err.data ? parseApiError(err.data, 'Не удалось проверить ЭЦП.') : err.message)
    } finally {
      setSigning(false)
    }
  }

  async function handleDevSign() {
    setError('')
    setSigning(true)
    try {
      await completeEcp((challenge) => buildDevCms(challenge))
    } catch (err) {
      setError(err.data ? parseApiError(err.data, 'Не удалось проверить тестовую ЭЦП.') : err.message)
    } finally {
      setSigning(false)
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setFieldErrors({})
    if (!ecpSessionToken) {
      setError('Сначала подпишите challenge электронной подписью.')
      return
    }
    if (!form.personal_data_consent) {
      setError('Необходимо согласие на обработку персональных данных.')
      return
    }
    setLoading(true)
    try {
      await registerWithEcp({
        ecp_session_token: ecpSessionToken,
        email: form.email,
        phone: form.phone,
        password: form.password,
        repeat_password: form.repeat_password,
        role: form.role,
        personal_data_consent: form.personal_data_consent,
      })
      await login(form.email, form.password)
      navigate(form.role === 'author' ? '/author' : '/')
    } catch (err) {
      if (!err.data && !err.status) {
        setError('Сервер недоступен.')
        return
      }
      const fields = parseApiFieldErrors(err.data)
      setFieldErrors(fields)
      setError(
        fields._form
          || (Object.keys(fields).filter((key) => key !== '_form').length === 0
            ? parseApiError(err.data, 'Не удалось зарегистрироваться.')
            : '')
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-lg px-4 py-16">
      <form onSubmit={handleSubmit} className="space-y-4 rounded-3xl bg-white p-8 shadow-md">
        <p className="text-sm font-semibold text-teal-600">е-Көмек</p>
        <h1 className="text-2xl font-semibold text-slate-800">Регистрация через ЭЦП</h1>
        <p className="text-sm text-slate-500">
          Подпишите одноразовый challenge в NCALayer. ФИО, ИИН и дата рождения заполнятся из сертификата и не редактируются.
        </p>
        <div className="space-y-2 rounded-2xl bg-sky-50 p-4">
          {ecpProfile ? (
            <div className="space-y-1 text-sm text-slate-700">
              <p><span className="text-slate-500">ФИО:</span> {ecpProfile.full_name}</p>
              <p><span className="text-slate-500">ИИН:</span> {ecpProfile.iin_masked}</p>
              <p><span className="text-slate-500">Дата рождения:</span> {ecpProfile.birth_date || '—'}</p>
              <p><span className="text-slate-500">Издатель:</span> {ecpProfile.issuer || '—'}</p>
            </div>
          ) : (
            <p className="text-sm text-slate-600">Сертификат ещё не подтверждён.</p>
          )}
          <button
            type="button"
            onClick={handleNcaLayerSign}
            disabled={signing}
            className="w-full rounded-2xl bg-slate-800 px-6 py-3 text-sm font-semibold text-white hover:bg-slate-900 disabled:opacity-60"
          >
            {signing ? 'Подписание...' : 'Подписать через NCALayer'}
          </button>
          {isDevEcpEnabled() && (
            <button
              type="button"
              onClick={handleDevSign}
              disabled={signing}
              className="w-full rounded-2xl border border-amber-300 bg-amber-50 px-6 py-3 text-sm font-semibold text-amber-800"
            >
              Локальный тестовый сертификат
            </button>
          )}
        </div>
        <div className="space-y-1">
          <input type="email" placeholder="Email" value={form.email} onChange={(e) => updateField('email', e.target.value)} required className={fieldClassName(fieldErrors.email)} />
          <FieldError message={fieldErrors.email} />
        </div>
        <div className="space-y-1">
          <input type="text" placeholder="Телефон" value={form.phone} onChange={(e) => updateField('phone', e.target.value)} required className={fieldClassName(fieldErrors.phone)} />
          <FieldError message={fieldErrors.phone} />
        </div>
        <div className="space-y-1">
          <select value={form.role} onChange={(e) => updateField('role', e.target.value)} className={fieldClassName(fieldErrors.role)}>
            <option value="donor">Донор</option>
            <option value="author">Автор сбора</option>
          </select>
          <FieldError message={fieldErrors.role} />
        </div>
        <div className="space-y-1">
          <PasswordInput placeholder="Пароль" value={form.password} onChange={(e) => updateField('password', e.target.value)} required minLength={8} className={passwordFieldClassName(fieldErrors.password)} />
          <FieldError message={fieldErrors.password} />
        </div>
        <div className="space-y-1">
          <PasswordInput placeholder="Повторите пароль" value={form.repeat_password} onChange={(e) => updateField('repeat_password', e.target.value)} required className={passwordFieldClassName(fieldErrors.repeat_password)} />
          <FieldError message={fieldErrors.repeat_password} />
        </div>
        <label className="flex items-start gap-3 text-sm text-slate-600">
          <input type="checkbox" checked={form.personal_data_consent} onChange={(e) => updateField('personal_data_consent', e.target.checked)} className="mt-1" />
          <span>Согласен(на) на обработку персональных данных</span>
        </label>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button type="submit" disabled={loading || !ecpSessionToken} className="w-full rounded-2xl bg-teal-500 px-6 py-4 font-semibold text-white hover:bg-teal-600 disabled:opacity-60">
          {loading ? 'Регистрация...' : 'Зарегистрироваться'}
        </button>
        <p className="text-center text-sm text-slate-600">
          Уже есть аккаунт?{' '}
          <Link to="/login" className="font-medium text-teal-600 hover:underline">Войти</Link>
        </p>
      </form>
    </div>
  )
}
