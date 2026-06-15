import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { createCard, parseApiError, submitCard, uploadDocument } from '../../api/client'

const initialForm = {
  full_name: '',
  diagnosis: '',
  city: '',
  clinic: '',
  age: '',
  gender: 'female',
  description: '',
  target_amount: '',
  end_date: '',
  iin: '',
  document_number: '',
  contact_phone: '',
  contact_email: '',
  personal_data_consent: false,
}

function FieldLabel({ children, required = false }) {
  return (
    <label className="block text-sm font-medium text-slate-700">
      {children}
      {required && <span className="text-red-500"> *</span>}
    </label>
  )
}

function inputClassName() {
  return 'w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500'
}

function FileUploadField({ id, accept, multiple, label, files, onChange }) {
  const selectedFiles = multiple ? files : files ? [files] : []

  return (
    <div className="space-y-2">
      <input
        id={id}
        type="file"
        accept={accept}
        multiple={multiple}
        onChange={onChange}
        className="sr-only"
      />
      <label
        htmlFor={id}
        className="inline-flex cursor-pointer items-center rounded-2xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm font-semibold text-teal-700 transition hover:bg-teal-100"
      >
        {label}
      </label>
      {selectedFiles.length > 0 && (
        <ul className="space-y-1 text-xs text-slate-500">
          {selectedFiles.map((file) => (
            <li key={`${file.name}-${file.lastModified}`}>{file.name}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

function appendIfPresent(formData, key, value) {
  if (value !== undefined && value !== null && value !== '') {
    formData.append(key, value)
  }
}

function buildFormData(form, photoFile) {
  const formData = new FormData()
  formData.append('full_name', form.full_name)
  formData.append('diagnosis', form.diagnosis)
  formData.append('city', form.city)
  appendIfPresent(formData, 'clinic', form.clinic)
  appendIfPresent(formData, 'age', form.age)
  appendIfPresent(formData, 'gender', form.gender)
  appendIfPresent(formData, 'description', form.description)
  formData.append('target_amount', form.target_amount)
  formData.append('end_date', form.end_date)
  appendIfPresent(formData, 'iin', form.iin)
  appendIfPresent(formData, 'document_number', form.document_number)
  appendIfPresent(formData, 'contact_phone', form.contact_phone)
  appendIfPresent(formData, 'contact_email', form.contact_email)
  formData.append('personal_data_consent', form.personal_data_consent ? 'true' : 'false')
  if (photoFile) {
    formData.append('photo_url', photoFile)
  }
  return formData
}

async function uploadDocuments(cardId, documentFiles) {
  for (const file of documentFiles) {
    const formData = new FormData()
    formData.append('file', file)
    await uploadDocument(cardId, formData)
  }
}

export default function CreateCard() {
  const navigate = useNavigate()
  const [form, setForm] = useState(initialForm)
  const [photoFile, setPhotoFile] = useState(null)
  const [documentFiles, setDocumentFiles] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  function validateConsent() {
    if (!form.personal_data_consent) {
      setError('Необходимо согласие на обработку персональных данных.')
      return false
    }
    return true
  }

  async function handleSave(submitForReview) {
    setError('')
    if (!validateConsent()) return
    setLoading(true)
    try {
      const card = await createCard(buildFormData(form, photoFile))
      await uploadDocuments(card.id, documentFiles)
      if (submitForReview) {
        await submitCard(card.id)
      }
      navigate('/author')
    } catch (err) {
      setError(parseApiError(err.data, 'Не удалось сохранить сбор.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 px-4 py-10">
      <Link to="/author" className="text-sm font-medium text-teal-600 hover:underline">
        ← Личный кабинет
      </Link>
      <form
        onSubmit={(event) => event.preventDefault()}
        className="space-y-5 rounded-3xl bg-white p-8 shadow-md"
      >
        <h1 className="text-2xl font-semibold text-slate-800">Создать сбор</h1>

        <div className="space-y-2">
          <FieldLabel required>ФИО получателя</FieldLabel>
          <input
            type="text"
            value={form.full_name}
            onChange={(e) => updateField('full_name', e.target.value)}
            required
            className={inputClassName()}
          />
        </div>

        <div className="space-y-2">
          <FieldLabel required>Диагноз</FieldLabel>
          <input
            type="text"
            value={form.diagnosis}
            onChange={(e) => updateField('diagnosis', e.target.value)}
            required
            className={inputClassName()}
          />
        </div>

        <div className="space-y-2">
          <FieldLabel required>Город</FieldLabel>
          <input
            type="text"
            value={form.city}
            onChange={(e) => updateField('city', e.target.value)}
            required
            className={inputClassName()}
          />
        </div>

        <div className="space-y-2">
          <FieldLabel>Поликлиника</FieldLabel>
          <input
            type="text"
            value={form.clinic}
            onChange={(e) => updateField('clinic', e.target.value)}
            className={inputClassName()}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <FieldLabel>Возраст</FieldLabel>
            <input
              type="number"
              min="0"
              value={form.age}
              onChange={(e) => updateField('age', e.target.value)}
              className={inputClassName()}
            />
          </div>
          <div className="space-y-2">
            <FieldLabel>Пол</FieldLabel>
            <select
              value={form.gender}
              onChange={(e) => updateField('gender', e.target.value)}
              className={inputClassName()}
            >
              <option value="female">Женский</option>
              <option value="male">Мужской</option>
            </select>
          </div>
        </div>

        <div className="space-y-2">
          <FieldLabel>Описание</FieldLabel>
          <textarea
            value={form.description}
            onChange={(e) => updateField('description', e.target.value)}
            rows={4}
            className={inputClassName()}
          />
        </div>

        <div className="space-y-2">
          <FieldLabel required>Целевая сумма</FieldLabel>
          <input
            type="number"
            min="1"
            step="0.01"
            value={form.target_amount}
            onChange={(e) => updateField('target_amount', e.target.value)}
            required
            className={inputClassName()}
          />
        </div>

        <div className="space-y-2">
          <FieldLabel required>Дата окончания сбора</FieldLabel>
          <input
            type="date"
            value={form.end_date}
            onChange={(e) => updateField('end_date', e.target.value)}
            required
            className={inputClassName()}
          />
        </div>

        <div className="space-y-2">
          <FieldLabel>ИИН</FieldLabel>
          <input
            type="text"
            value={form.iin}
            onChange={(e) => updateField('iin', e.target.value)}
            className={inputClassName()}
          />
        </div>

        <div className="space-y-2">
          <FieldLabel>Номер удостоверения</FieldLabel>
          <input
            type="text"
            value={form.document_number}
            onChange={(e) => updateField('document_number', e.target.value)}
            className={inputClassName()}
          />
        </div>

        <div className="space-y-2">
          <FieldLabel>Телефон для связи</FieldLabel>
          <input
            type="text"
            value={form.contact_phone}
            onChange={(e) => updateField('contact_phone', e.target.value)}
            className={inputClassName()}
          />
        </div>

        <div className="space-y-2">
          <FieldLabel>Email для связи</FieldLabel>
          <input
            type="email"
            value={form.contact_email}
            onChange={(e) => updateField('contact_email', e.target.value)}
            className={inputClassName()}
          />
        </div>

        <div className="space-y-2">
          <FieldLabel>Фото (JPG, PNG)</FieldLabel>
          <FileUploadField
            id="photo-upload"
            accept=".jpg,.jpeg,.png,image/jpeg,image/png"
            label="Выбрать фото"
            files={photoFile}
            onChange={(e) => setPhotoFile(e.target.files?.[0] || null)}
          />
        </div>

        <div className="space-y-2">
          <FieldLabel>Документы (PDF)</FieldLabel>
          <FileUploadField
            id="documents-upload"
            accept=".pdf,application/pdf"
            multiple
            label="Выбрать PDF"
            files={documentFiles}
            onChange={(e) => setDocumentFiles(Array.from(e.target.files || []))}
          />
        </div>

        <label className="flex items-start gap-3 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={form.personal_data_consent}
            onChange={(e) => updateField('personal_data_consent', e.target.checked)}
            className="mt-1"
            required
          />
          <span>Согласен(на) на обработку персональных данных</span>
        </label>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="grid gap-3 sm:grid-cols-2">
          <button
            type="button"
            disabled={loading}
            onClick={() => handleSave(false)}
            className="rounded-2xl border border-teal-200 px-6 py-4 font-semibold text-teal-700 hover:bg-teal-50 disabled:opacity-60"
          >
            {loading ? 'Сохранение...' : 'Сохранить черновик'}
          </button>
          <button
            type="button"
            disabled={loading}
            onClick={() => handleSave(true)}
            className="rounded-2xl bg-teal-500 px-6 py-4 font-semibold text-white hover:bg-teal-600 disabled:opacity-60"
          >
            {loading ? 'Отправка...' : 'Отправить на модерацию'}
          </button>
        </div>
      </form>
    </div>
  )
}
