import { useEffect, useState } from 'react'
import {
  fetchBeneficiaries,
  parseApiError,
  requestEcpChallenge,
  verifyCardRecipient,
} from '../api/client'
import { buildDevCms, isDevEcpEnabled, signChallengeWithNcaLayer } from '../api/ncalayer'

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

export default function RecipientVerifyPanel({ onVerified }) {
  const [kind, setKind] = useState('self')
  const [relationshipType, setRelationshipType] = useState('parent')
  const [sourceIin, setSourceIin] = useState('')
  const [existingId, setExistingId] = useState('')
  const [beneficiaries, setBeneficiaries] = useState([])
  const [beneficiary, setBeneficiary] = useState(null)
  const [lookupMessage, setLookupMessage] = useState('')
  const [signing, setSigning] = useState(false)

  useEffect(() => {
    fetchBeneficiaries().then(setBeneficiaries).catch(() => setBeneficiaries([]))
  }, [])

  function resetCurrent() {
    setBeneficiary(null)
    setLookupMessage('')
    onVerified({ token: '', beneficiary: null })
  }

  async function applyVerification(payload) {
    const verified = await verifyCardRecipient(payload)
    setBeneficiary(verified)
    onVerified({ token: verified.recipient_session_token, beneficiary: verified })
    if (verified.requires_manual_review) {
      setLookupMessage('Данные неполные или требуют ручной проверки. Карточка не будет опубликована автоматически.')
    } else {
      setLookupMessage('Получатель подтверждён. Поля из источника заполнены и не редактируются.')
    }
  }

  async function run(action) {
    setLookupMessage('')
    setSigning(true)
    try {
      await action()
    } catch (err) {
      setLookupMessage(err.data ? parseApiError(err.data, 'Не удалось подтвердить получателя.') : err.message)
    } finally {
      setSigning(false)
    }
  }

  return (
    <div className="space-y-3 rounded-2xl bg-sky-50 p-4">
      {beneficiaries.length > 0 && (
        <div className="space-y-2">
          <FieldLabel>Сохранённый получатель</FieldLabel>
          <select
            value={existingId}
            onChange={(event) => setExistingId(event.target.value)}
            aria-label="Сохранённый получатель"
            className={inputClassName()}
          >
            <option value="">Новый получатель</option>
            {beneficiaries.map((item) => (
              <option key={item.id} value={item.id}>
                {item.full_name || `Получатель #${item.id}`}
              </option>
            ))}
          </select>
          {existingId && (
            <button
              type="button"
              disabled={signing}
              onClick={() => run(() => applyVerification({ beneficiary_id: Number(existingId) }))}
              className="w-full rounded-2xl bg-slate-800 px-6 py-3 text-sm font-semibold text-white disabled:opacity-60"
            >
              {signing ? 'Проверка...' : 'Использовать выбранного получателя'}
            </button>
          )}
        </div>
      )}

      {!existingId && (
        <>
          <div className="space-y-2">
            <FieldLabel required>Для кого сбор</FieldLabel>
            <select
              value={kind}
              onChange={(event) => {
                setKind(event.target.value)
                resetCurrent()
              }}
              aria-label="Для кого сбор"
              className={inputClassName()}
            >
              <option value="self">Для себя</option>
              <option value="child">Для ребёнка / подопечного</option>
              <option value="other">Для другого человека</option>
            </select>
          </div>
          {kind === 'child' && (
            <div className="space-y-2">
              <FieldLabel>Тип представительства</FieldLabel>
              <select
                value={relationshipType}
                onChange={(event) => setRelationshipType(event.target.value)}
                aria-label="Тип представительства"
                className={inputClassName()}
              >
                <option value="parent">Родитель</option>
                <option value="guardian">Опекун</option>
              </select>
            </div>
          )}
        </>
      )}

      {beneficiary ? (
        <div className="space-y-1 text-sm text-slate-700">
          <p><span className="text-slate-500">ФИО:</span> {beneficiary.full_name || '—'}</p>
          <p><span className="text-slate-500">ИИН:</span> {beneficiary.iin_masked || '—'}</p>
          <p><span className="text-slate-500">Дата рождения:</span> {beneficiary.birth_date || '—'}</p>
          <p><span className="text-slate-500">Возраст:</span> {beneficiary.age ?? '—'}</p>
          <p><span className="text-slate-500">Город:</span> {beneficiary.city || '—'}</p>
          <p><span className="text-slate-500">Диагноз:</span> {beneficiary.diagnosis || '—'}</p>
          <p><span className="text-slate-500">Представительство:</span> {beneficiary.representation_status}</p>
        </div>
      ) : (
        <p className="text-sm text-slate-600">Получатель ещё не подтверждён.</p>
      )}

      {!existingId && kind === 'self' && (
        <button
          type="button"
          onClick={() => run(() => applyVerification({ kind: 'self' }))}
          disabled={signing}
          className="w-full rounded-2xl bg-slate-800 px-6 py-3 text-sm font-semibold text-white disabled:opacity-60"
        >
          {signing ? 'Проверка...' : 'Подтвердить получателя по ЭЦП автора'}
        </button>
      )}
      {!existingId && kind !== 'self' && (
        <>
          <button
            type="button"
            disabled={signing}
            onClick={() => run(async () => {
              const challenge = await requestEcpChallenge()
              const cms = await signChallengeWithNcaLayer(challenge.challenge)
              await applyVerification({
                kind,
                relationship_type: kind === 'child' ? relationshipType : 'representative',
                challenge_id: challenge.challenge_id,
                cms,
              })
            })}
            className="w-full rounded-2xl bg-slate-800 px-6 py-3 text-sm font-semibold text-white disabled:opacity-60"
          >
            {signing ? 'Подписание...' : 'Подписать ЭЦП получателя в NCALayer'}
          </button>
          <div className="flex gap-2">
            <input
              type="text"
              value={sourceIin}
              onChange={(event) => setSourceIin(event.target.value.replace(/\D/g, '').slice(0, 12))}
              maxLength={12}
              placeholder="Поиск в официальном источнике"
              aria-label="ИИН получателя"
              className={inputClassName()}
            />
            <button
              type="button"
              disabled={signing}
              onClick={() => run(() => {
                if (!/^\d{12}$/.test(sourceIin)) {
                  throw new Error('Для поиска в источнике укажите 12-значный ИИН.')
                }
                return applyVerification({
                  kind,
                  relationship_type: kind === 'child' ? relationshipType : 'representative',
                  source_iin: sourceIin,
                })
              })}
              className="shrink-0 rounded-2xl border border-teal-200 px-4 py-3 text-sm font-semibold text-teal-700"
            >
              Найти
            </button>
          </div>
          {isDevEcpEnabled() && (
            <button
              type="button"
              disabled={signing}
              onClick={() => run(async () => {
                const challenge = await requestEcpChallenge()
                await applyVerification({
                  kind,
                  relationship_type: kind === 'child' ? relationshipType : 'representative',
                  challenge_id: challenge.challenge_id,
                  cms: buildDevCms(challenge.challenge, { iin: sourceIin || undefined }),
                })
              })}
              className="w-full rounded-2xl border border-amber-300 bg-amber-50 px-6 py-3 text-sm font-semibold text-amber-800"
            >
              Локальный тестовый сертификат
            </button>
          )}
        </>
      )}
      {lookupMessage && <p className="text-sm text-slate-600">{lookupMessage}</p>}
    </div>
  )
}
