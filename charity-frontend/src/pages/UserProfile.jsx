import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchUserProfile, mediaUrl, parseApiError, updateUserProfile } from '../api/client'
import { useCurrentUser } from '../hooks/useCurrentUser'
import { ecpStatusLabel, formatDate, formatDateTime, roleLabel, userStatusLabel } from '../utils/format'

function Field({ label, value }) {
  if (value == null || value === '') return null
  return (
    <div>
      <p className="text-xs text-slate-500">{label}</p>
      <p className="font-medium text-slate-800">{value}</p>
    </div>
  )
}

export default function UserProfile() {
  const { userId } = useParams()
  const { user } = useCurrentUser()
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [adminName, setAdminName] = useState('')
  const [adminBirthDate, setAdminBirthDate] = useState('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  function load() {
    setLoading(true)
    fetchUserProfile(userId)
      .then((data) => {
        setProfile(data)
        setAdminName(data.full_name || '')
        setAdminBirthDate(data.birth_date || '')
      })
      .catch((err) => {
        setProfile(null)
        setError(parseApiError(err.data, err.status === 404 ? 'Профиль не найден.' : 'Не удалось загрузить профиль.'))
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [userId])

  async function handleAdminSave(event) {
    event.preventDefault()
    setSaving(true)
    setMessage('')
    setError('')
    try {
      const updated = await updateUserProfile(userId, {
        full_name: adminName,
        birth_date: adminBirthDate || null,
      })
      setProfile(updated)
      setMessage('Данные обновлены администратором.')
    } catch (err) {
      setError(parseApiError(err.data, 'Не удалось обновить профиль.'))
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <div className="mx-auto max-w-2xl px-4 py-16 text-center text-slate-500">Загрузка профиля...</div>
  }

  if (!profile) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 text-center">
        <p className="text-slate-600">{error || 'Профиль скрыт или не создан.'}</p>
        <Link to="/" className="mt-4 inline-block text-sm font-medium text-teal-600">На главную</Link>
      </div>
    )
  }

  const isOwn = user && Number(userId) === Number(user.id)
  const isStaff = profile.view === 'staff'
  const avatar = mediaUrl(profile.avatar)

  return (
    <div className="mx-auto max-w-2xl space-y-6 px-4 py-10">
      {isOwn && (
        <Link to="/profile" className="text-sm font-medium text-teal-600">Редактировать свой профиль</Link>
      )}
      <section className="space-y-5 rounded-3xl bg-white p-8 shadow-md">
        <div className="flex items-center gap-4">
          {avatar ? (
            <img src={avatar} alt="" className="h-20 w-20 rounded-full object-cover" />
          ) : (
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-sky-100 text-xl font-semibold text-teal-700">
              {(profile.full_name || '?').slice(0, 1)}
            </div>
          )}
          <div>
            <h1 className="text-2xl font-semibold text-slate-800">{profile.full_name || 'Пользователь'}</h1>
            {profile.role && <p className="text-sm text-slate-500">{roleLabel(profile.role)}</p>}
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Город" value={profile.city} />
          <Field label="Возраст" value={profile.age} />
          <Field label="Дата рождения" value={profile.birth_date ? formatDate(profile.birth_date) : null} />
          <Field label="Email" value={profile.email} />
          <Field label="Телефон" value={profile.phone} />
          <Field label="ЭЦП" value={profile.ecp_status ? ecpStatusLabel(profile.ecp_status) : null} />
        </div>
        {profile.bio && <p className="text-sm text-slate-700">{profile.bio}</p>}
        {!profile.full_name && !profile.bio && !profile.city && (
          <p className="text-sm text-slate-500">Пользователь не открыл публичные данные.</p>
        )}
      </section>

      {isStaff && (
        <section className="space-y-3 rounded-3xl bg-white p-8 shadow-md">
          <h2 className="text-lg font-semibold text-slate-800">Расширенный профиль</h2>
          <div className="grid gap-4 sm:grid-cols-2 text-sm">
            <Field label="Статус проверки" value={userStatusLabel(profile.verification_status)} />
            <Field label="ИИН" value={profile.iin_masked} />
            <Field label="Регистрация" value={formatDate(profile.registered_at || profile.created_at)} />
            <Field label="Последний вход" value={formatDateTime(profile.last_login_at)} />
          </div>
        </section>
      )}

      {user?.role === 'admin' && (
        <form onSubmit={handleAdminSave} className="space-y-4 rounded-3xl bg-white p-8 shadow-md">
          <h2 className="text-lg font-semibold text-slate-800">Изменение полей ЭЦП</h2>
          <label className="block space-y-1 text-sm">
            <span className="text-slate-600">ФИО</span>
            <input value={adminName} onChange={(e) => setAdminName(e.target.value)} className="w-full rounded-2xl border border-sky-100 px-4 py-3" />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="text-slate-600">Дата рождения</span>
            <input type="date" value={adminBirthDate} onChange={(e) => setAdminBirthDate(e.target.value)} className="w-full rounded-2xl border border-sky-100 px-4 py-3" />
          </label>
          {message && <p className="text-sm text-teal-700">{message}</p>}
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button type="submit" disabled={saving} className="rounded-2xl bg-slate-800 px-5 py-3 text-sm font-semibold text-white disabled:opacity-60">
            {saving ? 'Сохранение...' : 'Сохранить как администратор'}
          </button>
        </form>
      )}
    </div>
  )
}
