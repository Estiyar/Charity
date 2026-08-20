import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { createCard, parseApiError, submitCard, uploadDocument } from '../../api/client'
import FileUploadField from '../../components/FileUploadField'
import RecipientVerifyPanel from '../../components/RecipientVerifyPanel'

const initialForm = {
  description: '',
  target_amount: '',
  end_date: '',
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

function appendIfPresent(formData, key, value) {
  if (value !== undefined && value !== null && value !== '') {
    formData.append(key, value)
  }
}

function buildFormData(form, photoFile, recipientSessionToken) {
  const formData = new FormData()
  formData.append('recipient_session_token', recipientSessionToken)
  appendIfPresent(formData, 'description', form.description)
  formData.append('target_amount', form.target_amount)
  formData.append('end_date', form.end_date)
  appendIfPresent(formData, 'document_number', form.document_number)
  appendIfPresent(formData, 'contact_phone', form.contact_phone)
  appendIfPresent(formData, 'contact_email', form.contact_email)
  formData.append('personal_data_consent', form.personal_data_consent ? 'true' : 'false')
  if (photoFile) {
    formData.append('photo_url', photoFile)
  }
  return formData
}

async function uploadDocuments(cardId, documentFiles, extras) {
  for (const file of documentFiles) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('document_type', extras.document_type || 'medical')
    if (extras.issuer) formData.append('issuer', extras.issuer)
    if (extras.issued_at) formData.append('issued_at', extras.issued_at)
    if (extras.expires_at) formData.append('expires_at', extras.expires_at)
    await uploadDocument(cardId, formData)
  }
}

export default function CreateCard() {
  const navigate = useNavigate()
  const [form, setForm] = useState(initialForm)
  const [recipientSessionToken, setRecipientSessionToken] = useState('')
  const [photoFile, setPhotoFile] = useState(null)
  const [documentFiles, setDocumentFiles] = useState([])
  const [documentMeta, setDocumentMeta] = useState({ issuer: '', issued_at: '', expires_at: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function handleSave(submitForReview) {
    setError('')
    if (!recipientSessionToken) {
      setError('Сначала подтвердите получателя.')
      return
    }
    if (!form.personal_data_consent) {
      setError('Необходимо согласие на обработку персональных данных.')
      return
    }
    setLoading(true)
    try {
      const card = await createCard(buildFormData(form, photoFile, recipientSessionToken))
      await uploadDocuments(card.id, documentFiles, documentMeta)
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
      <form onSubmit={(event) => event.preventDefault()} className="space-y-5 rounded-3xl bg-white p-8 shadow-md">
        <h1 className="text-2xl font-semibold text-slate-800">Создать сбор</h1>
        <p className="text-sm text-slate-500">
          Получатель — отдельная сущность. Подтвердите его ЭЦП, официальным источником или выберите сохранённого.
        </p>
        <RecipientVerifyPanel
          onVerified={({ token }) => setRecipientSessionToken(token || '')}
        />
        <div className="space-y-2">
          <FieldLabel>Описание</FieldLabel>
          <textarea value={form.description} onChange={(e) => updateField('description', e.target.value)} rows={4} aria-label="Описание" className={inputClassName()} />
        </div>
        <div className="space-y-2">
          <FieldLabel required>Целевая сумма</FieldLabel>
          <input type="number" min="1" step="0.01" value={form.target_amount} onChange={(e) => updateField('target_amount', e.target.value)} required aria-label="Целевая сумма" className={inputClassName()} />
        </div>
        <div className="space-y-2">
          <FieldLabel required>Дата окончания сбора</FieldLabel>
          <input type="date" value={form.end_date} onChange={(e) => updateField('end_date', e.target.value)} required aria-label="Дата окончания сбора" className={inputClassName()} />
        </div>
        <div className="space-y-2">
          <FieldLabel>Номер удостоверения</FieldLabel>
          <input type="text" value={form.document_number} onChange={(e) => updateField('document_number', e.target.value)} aria-label="Номер удостоверения" className={inputClassName()} />
        </div>
        <div className="space-y-2">
          <FieldLabel>Телефон для связи</FieldLabel>
          <input type="text" value={form.contact_phone} onChange={(e) => updateField('contact_phone', e.target.value)} aria-label="Телефон для связи" className={inputClassName()} />
        </div>
        <div className="space-y-2">
          <FieldLabel>Email для связи</FieldLabel>
          <input type="email" value={form.contact_email} onChange={(e) => updateField('contact_email', e.target.value)} aria-label="Email для связи" className={inputClassName()} />
        </div>
        <div className="space-y-2">
          <FieldLabel>Фото (JPG, PNG)</FieldLabel>
          <FileUploadField id="photo-upload" accept=".jpg,.jpeg,.png,image/jpeg,image/png" label="Выбрать фото" files={photoFile} onChange={(e) => setPhotoFile(e.target.files?.[0] || null)} />
        </div>
        <div className="space-y-2">
          <FieldLabel>Документы представительства / меддокументы (PDF, JPG, PNG)</FieldLabel>
          <FileUploadField id="documents-upload" accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png" multiple label="Выбрать файлы" files={documentFiles} onChange={(e) => setDocumentFiles(Array.from(e.target.files || []))} />
          <input value={documentMeta.issuer} onChange={(e) => setDocumentMeta((current) => ({ ...current, issuer: e.target.value }))} placeholder="Клиника / организация" aria-label="Клиника или организация" className={inputClassName()} />
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-2">
              <FieldLabel>Дата выдачи</FieldLabel>
              <input type="date" value={documentMeta.issued_at} onChange={(e) => setDocumentMeta((current) => ({ ...current, issued_at: e.target.value }))} aria-label="Дата выдачи документа" className={inputClassName()} />
            </div>
            <div className="space-y-2">
              <FieldLabel>Срок действия</FieldLabel>
              <input type="date" value={documentMeta.expires_at} onChange={(e) => setDocumentMeta((current) => ({ ...current, expires_at: e.target.value }))} aria-label="Срок действия документа" className={inputClassName()} />
            </div>
          </div>
        </div>
        <label className="flex items-start gap-3 text-sm text-slate-600">
          <input type="checkbox" checked={form.personal_data_consent} onChange={(e) => updateField('personal_data_consent', e.target.checked)} className="mt-1" required />
          <span>Согласен(на) на обработку персональных данных</span>
        </label>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="grid gap-3 sm:grid-cols-2">
          <button type="button" disabled={loading || !recipientSessionToken} onClick={() => handleSave(false)} className="rounded-2xl border border-teal-200 px-6 py-4 font-semibold text-teal-700 disabled:opacity-60">
            {loading ? 'Сохранение...' : 'Сохранить черновик'}
          </button>
          <button type="button" disabled={loading || !recipientSessionToken} onClick={() => handleSave(true)} className="rounded-2xl bg-teal-500 px-6 py-4 font-semibold text-white disabled:opacity-60">
            {loading ? 'Отправка...' : 'Отправить на модерацию'}
          </button>
        </div>
      </form>
    </div>
  )
}
