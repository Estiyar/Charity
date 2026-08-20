import { useEffect, useState } from 'react'
import { fetchBeneficiaries, fetchRepresentations, updateBeneficiary, verifyRepresentation } from '../../api/client'
import {
  formatDateTime,
  relationshipLabel,
  representationMethodLabel,
  representationStatusLabel,
  userStatusLabel,
} from '../../utils/format'

export default function AuthorBeneficiaries() {
  const [beneficiaries, setBeneficiaries] = useState([])
  const [representations, setRepresentations] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  function load() {
    setLoading(true)
    Promise.all([fetchBeneficiaries(), fetchRepresentations()])
      .then(([people, links]) => {
        setBeneficiaries(people)
        setRepresentations(links)
      })
      .catch(() => setError('Не удалось загрузить получателей.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  async function submitDocuments(representationId) {
    const raw = window.prompt('ID подтверждающих документов через запятую')
    if (!raw) return
    const documentIds = raw.split(',').map((item) => Number(item.trim())).filter(Boolean)
    try {
      await verifyRepresentation({
        representation_id: representationId,
        verification_method: 'document',
        document_ids: documentIds,
      })
      load()
    } catch {
      setError('Не удалось отправить документы на проверку.')
    }
  }

  async function hideDiagnosis(beneficiary) {
    try {
      await updateBeneficiary(beneficiary.id, {
        public_fields: (beneficiary.public_fields || []).filter((field) => field !== 'diagnosis'),
      })
      load()
    } catch {
      setError('Не удалось обновить публичность.')
    }
  }

  if (loading) {
    return <div className="rounded-3xl bg-white p-8 text-slate-500 shadow-md">Загрузка...</div>
  }

  return (
    <div className="space-y-6">
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      <section className="rounded-3xl bg-white p-6 shadow-md">
        <h2 className="mb-4 text-xl font-semibold text-slate-800">Получатели</h2>
        {!beneficiaries.length ? (
          <p className="text-slate-500">Пока нет сохранённых получателей. Они появятся после подтверждения при создании сбора.</p>
        ) : (
          <div className="space-y-3">
            {beneficiaries.map((item) => (
              <article key={item.id} className="rounded-2xl bg-sky-50 p-4">
                <p className="font-medium text-slate-800">{item.full_name || `Получатель #${item.id}`}</p>
                <p className="text-sm text-slate-500">
                  {item.iin_masked} · {item.city || 'город не указан'} · {userStatusLabel(item.verification_status)}
                </p>
                <p className="text-xs text-slate-400">
                  Медданные: {item.medical_linked ? item.medical_source || 'связаны' : 'нет'}
                  {item.last_checked_at ? ` · проверка ${formatDateTime(item.last_checked_at)}` : ''}
                </p>
                <button
                  type="button"
                  onClick={() => hideDiagnosis(item)}
                  className="mt-2 text-sm font-medium text-teal-700"
                >
                  Скрыть диагноз в публичных полях
                </button>
              </article>
            ))}
          </div>
        )}
      </section>
      <section className="rounded-3xl bg-white p-6 shadow-md">
        <h2 className="mb-4 text-xl font-semibold text-slate-800">Представительство</h2>
        {!representations.length ? (
          <p className="text-slate-500">Нет записей представительства.</p>
        ) : (
          <div className="space-y-3">
            {representations.map((item) => (
              <article key={item.id} className="rounded-2xl bg-slate-50 p-4">
                <p className="font-medium text-slate-800">{item.beneficiary_name}</p>
                <p className="text-sm text-slate-500">
                  {relationshipLabel(item.relationship_type)} · {representationMethodLabel(item.verification_method)}
                  {' · '}
                  {representationStatusLabel(item.verification_status)}
                </p>
                {item.rejection_reason ? <p className="text-sm text-red-600">{item.rejection_reason}</p> : null}
                {['pending', 'manual_review', 'rejected'].includes(item.verification_status) && item.relationship_type !== 'self' && (
                  <button
                    type="button"
                    onClick={() => submitDocuments(item.id)}
                    className="mt-2 rounded-2xl bg-teal-500 px-4 py-2 text-sm font-semibold text-white"
                  >
                    Отправить документы на проверку
                  </button>
                )}
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
