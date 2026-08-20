import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchMyProfile, mediaUrl, parseApiError, parseApiFieldErrors, updateMyProfile } from '../api/client'
import FileUploadField from '../components/FileUploadField'
import { ecpStatusLabel, formatDate, formatDateTime, roleLabel, userStatusLabel } from '../utils/format'

const PUBLIC_FIELD_OPTIONS = [
  { id: 'full_name', label: 'ФИО' },
  { id: 'avatar', label: 'Фото' },
  { id: 'bio', label: 'Описание' },
  { id: 'city', label: 'Город' },
  { id: 'role', label: 'Роль' },
  { id: 'age', label: 'Возраст' },
  { id: 'birth_date', label: 'Дата рождения' },
  { id: 'email', label: 'Email' },
  { id: 'phone', label: 'Телефон' },
  { id: 'ecp_status', label: 'Статус ЭЦП' },
]

function inputClassName(hasError) {
  return `w-full rounded-2xl border px-4 py-3 text-sm outline-none focus:border-teal-500 ${
    hasError ? 'border-red-300' : 'border-sky-100'
  }`
}

export default function Profile() {
  const [profile, setProfile] = useState(null)
  const [form, setForm] = useState({ bio: '', city: '', phone: '', public_fields: [] })
  const [avatarFile, setAvatarFile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const [message, setMessage] = useState('')

  useEffect(() => {
    setLoading(true)
    fetchMyProfile()
      .then((data) => {
        setProfile(data)
        setForm({
          bio: data.bio || '',
          city: data.city || '',
          phone: data.phone || '',
          public_fields: data.public_fields || [],
        })
      })
      .catch((err) => setError(parseApiError(err.data, 'Не удалось загрузить профиль.')))
      .finally(() => setLoading(false))
  }, [])

  function togglePublicField(field) {
    setForm((prev) => {
      const selected = new Set(prev.public_fields)
      if (selected.has(field)) selected.delete(field)
      else selected.add(field)
      return { ...prev, public_fields: Array.from(selected) }
    })
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setMessage('')
    setFieldErrors({})
    const digits = (form.phone || '').replace(/\D/g, '')
    if (form.phone && digits.length < 10) {
      setFieldErrors({ phone: 'Укажите корректный номер телефона.' })
      return
    }
    setSaving(true)
    try {
      let payload
      if (avatarFile) {
        payload = new FormData()
        payload.append('bio', form.bio)
        payload.append('city', form.city)
        payload.append('phone', form.phone)
        payload.append('public_fields', JSON.stringify(form.public_fields))
        payload.append('avatar', avatarFile)
      } else {
        payload = {
          bio: form.bio,
          city: form.city,
          phone: form.phone,
          public_fields: form.public_fields,
        }
      }
      const updated = await updateMyProfile(payload)
      setProfile(updated)
      setMessage('Профиль сохранён.')
    } catch (err) {
      setFieldErrors(parseApiFieldErrors(err.data))
      setError(parseApiError(err.data, 'Не удалось сохранить профиль.'))
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
        <p className="text-slate-600">{error || 'Профиль не найден.'}</p>
        <Link to="/" className="mt-4 inline-block text-sm font-medium text-teal-600">На главную</Link>
      </div>
    )
  }

  const avatar = mediaUrl(profile.avatar)
  const locked = new Set(profile.locked_fields || [])

  return (
    <div className="mx-auto max-w-2xl space-y-6 px-4 py-10">
      <h1 className="text-2xl font-semibold text-slate-800">Мой профиль</h1>
      <form onSubmit={handleSubmit} className="space-y-5 rounded-3xl bg-white p-8 shadow-md">
        <div className="flex items-center gap-4">
          {avatar ? (
            <img src={avatar} alt="" className="h-20 w-20 rounded-full object-cover" />
          ) : (
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-sky-100 text-xl font-semibold text-teal-700">
              {(profile.full_name || '?').slice(0, 1)}
            </div>
          )}
          <FileUploadField
            id="avatar-upload"
            accept=".jpg,.jpeg,.png,image/jpeg,image/png"
            label="Загрузить фото"
            files={avatarFile}
            onChange={(e) => setAvatarFile(e.target.files?.[0] || null)}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <p className="text-xs text-slate-500">ФИО {locked.has('full_name') ? '(ЭЦП)' : ''}</p>
            <p className="font-medium text-slate-800">{profile.full_name || '—'}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Роль</p>
            <p className="font-medium text-slate-800">{roleLabel(profile.role)}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Email</p>
            <p className="font-medium text-slate-800">{profile.email || '—'}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Статус проверки</p>
            <p className="font-medium text-slate-800">{userStatusLabel(profile.verification_status)}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">ЭЦП</p>
            <p className="font-medium text-slate-800">{ecpStatusLabel(profile.ecp_status)}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Дата рождения / возраст</p>
            <p className="font-medium text-slate-800">
              {profile.birth_date ? formatDate(profile.birth_date) : '—'}
              {profile.age != null ? ` · ${profile.age}` : ''}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Регистрация</p>
            <p className="font-medium text-slate-800">{formatDate(profile.registered_at || profile.created_at)}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Последний вход</p>
            <p className="font-medium text-slate-800">{formatDateTime(profile.last_login_at)}</p>
          </div>
        </div>

        <label className="block space-y-1">
          <span className="text-sm font-medium text-slate-700">Город</span>
          <input value={form.city} onChange={(e) => setForm((prev) => ({ ...prev, city: e.target.value }))} maxLength={128} className={inputClassName(fieldErrors.city)} />
        </label>
        <label className="block space-y-1">
          <span className="text-sm font-medium text-slate-700">Телефон</span>
          <input value={form.phone} onChange={(e) => setForm((prev) => ({ ...prev, phone: e.target.value }))} className={inputClassName(fieldErrors.phone)} />
          {fieldErrors.phone && <p className="text-xs text-red-600">{fieldErrors.phone}</p>}
        </label>
        <label className="block space-y-1">
          <span className="text-sm font-medium text-slate-700">О себе</span>
          <textarea value={form.bio} onChange={(e) => setForm((prev) => ({ ...prev, bio: e.target.value }))} rows={4} maxLength={2000} className={inputClassName(fieldErrors.bio)} />
        </label>

        <fieldset className="space-y-2 rounded-2xl bg-sky-50 p-4">
          <legend className="text-sm font-medium text-slate-700">Публичные поля</legend>
          <p className="text-xs text-slate-500">На публичной странице будут только отмеченные данные.</p>
          <div className="grid gap-2 sm:grid-cols-2">
            {PUBLIC_FIELD_OPTIONS.map((option) => (
              <label key={option.id} className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={form.public_fields.includes(option.id)}
                  onChange={() => togglePublicField(option.id)}
                />
                {option.label}
              </label>
            ))}
          </div>
        </fieldset>

        {locked.size > 0 && (
          <p className="text-xs text-slate-500">
            ФИО и дата рождения из ЭЦП меняются только повторной проверкой или администратором.
          </p>
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {message && <p className="text-sm text-teal-700">{message}</p>}
        <button type="submit" disabled={saving} className="w-full rounded-2xl bg-teal-500 px-6 py-3 font-semibold text-white disabled:opacity-60">
          {saving ? 'Сохранение...' : 'Сохранить'}
        </button>
      </form>
    </div>
  )
}
