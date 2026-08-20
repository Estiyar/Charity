import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { decideManualReview, fetchManualReview } from '../../api/client'
import ModeratorCommentFields, { CommentHistory } from '../../components/ModeratorCommentFields'
import { formatDateTime, statusLabel } from '../../utils/format'

const ACTION_LABELS = {
  approve: 'Одобрить',
  reject: 'Отклонить',
  request_revision: 'На доработку',
  'request-revision': 'На доработку',
  suspend: 'Приостановить',
  unsuspend: 'Снять приостановку',
}

const ACTION_PATHS = {
  approve: 'approve',
  reject: 'reject',
  request_revision: 'request-revision',
  suspend: 'suspend',
  unsuspend: 'unsuspend',
}

function signalText(item) {
  if (typeof item === 'string') return item
  if (item?.message) {
    const ids = (item.matched_card_ids || []).join(', ')
    return ids ? `${item.message} Карточки: ${ids}` : item.message
  }
  return JSON.stringify(item)
}

function ReasonList({ title, items }) {
  const values = items || []
  return (
    <section className="rounded-3xl bg-white p-6 shadow-md">
      <h2 className="mb-3 text-lg font-semibold text-slate-800">{title}</h2>
      {values.length ? (
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
          {values.map((item, index) => (
            <li key={item?.code || String(item) || index}>{signalText(item)}</li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-slate-500">Нет данных</p>
      )}
    </section>
  )
}

export default function ManualReviewDetail() {
  const { id } = useParams()
  const [review, setReview] = useState(null)
  const [revisionComment, setRevisionComment] = useState('')
  const [internalComment, setInternalComment] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchManualReview(id).then(setReview).catch(() => setReview(null))
  }, [id])

  async function runAction(action) {
    setError('')
    setMessage('')
    setLoading(true)
    try {
      const result = await decideManualReview(id, ACTION_PATHS[action], {
        comment: revisionComment,
        revision_comment: revisionComment,
        internal_comment: internalComment,
        evidence_reviewed: [
          'risk_score',
          'risk_reasons',
          'verification_snapshot',
          'duplicate_signals',
          'document_metadata',
          'audit_history',
        ],
        idempotency_key: `${id}:${action}`,
      })
      setReview(result)
      setMessage('Решение сохранено')
      setRevisionComment('')
      setInternalComment('')
    } catch (err) {
      setError(err.data?.detail || err.data?.comment?.[0] || 'Не удалось выполнить действие')
    } finally {
      setLoading(false)
    }
  }

  if (!review) {
    return <div className="rounded-3xl bg-white p-8 text-slate-500 shadow-md">Загрузка...</div>
  }

  const verification = review.verification_snapshot || {}

  return (
    <div className="space-y-6">
      <Link to="/moderator/reviews" className="text-sm font-medium text-teal-600 hover:underline">
        ← К очереди высокого риска
      </Link>
      <section className="rounded-3xl bg-white p-6 shadow-md">
        <h1 className="text-2xl font-semibold text-slate-800">{review.subject_label}</h1>
        <p className="mt-2 text-sm text-slate-500">
          {review.subject_type === 'user' ? 'Пользователь' : 'Карточка'} #{review.subject_id}
          {' · '}
          {statusLabel(review.status)}
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div className="rounded-2xl bg-rose-50 p-4">
            <p className="text-xs uppercase text-slate-500">Risk score</p>
            <p className="text-xl font-semibold text-slate-800">{review.risk_score}</p>
          </div>
          <div className="rounded-2xl bg-rose-50 p-4">
            <p className="text-xs uppercase text-slate-500">Уровень</p>
            <p className="text-xl font-semibold text-slate-800">{review.risk_level || '—'}</p>
          </div>
          <div className="rounded-2xl bg-rose-50 p-4">
            <p className="text-xs uppercase text-slate-500">Предыдущий статус</p>
            <p className="text-xl font-semibold text-slate-800">{statusLabel(review.previous_subject_status)}</p>
          </div>
        </div>
      </section>
      <ReasonList title="Причины риска" items={review.risk_reasons} />
      <ReasonList title="Сигналы дублей" items={review.duplicate_signals} />
      <section className="rounded-3xl bg-white p-6 shadow-md">
        <h2 className="mb-3 text-lg font-semibold text-slate-800">Результаты проверки</h2>
        <div className="space-y-2 text-sm text-slate-700">
          <p>Антифрод: {verification.fraud?.risk_level || verification.fraud?.risk_score || 'нет профиля'}</p>
          <p>Медреестр: {verification.medical?.diagnosis || verification.medical?.full_name || 'нет записи'}</p>
          <p>ЭЦП: {verification.ecp?.certificate_type || verification.ecp?.full_name || 'нет проверки'}</p>
          <p>ИИН: {verification.iin_masked || '—'}</p>
        </div>
      </section>
      <section className="rounded-3xl bg-white p-6 shadow-md">
        <h2 className="mb-3 text-lg font-semibold text-slate-800">Документы</h2>
        {(review.document_metadata || []).length ? (
          <ul className="space-y-2 text-sm text-slate-700">
            {review.document_metadata.map((doc) => (
              <li key={doc.id} className="rounded-2xl bg-sky-50 px-4 py-3">
                {doc.file_name} · {doc.file_type} · {statusLabel(doc.status)}
                {doc.has_confidential ? ' · конфиденциально' : ''}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-slate-500">Метаданные документов отсутствуют</p>
        )}
      </section>
      {review.comments?.length > 0 && (
        <section className="rounded-3xl bg-white p-6 shadow-md">
          <h2 className="mb-3 text-lg font-semibold text-slate-800">Комментарии</h2>
          <CommentHistory comments={review.comments} />
        </section>
      )}
      <section className="rounded-3xl bg-white p-6 shadow-md">
        <h2 className="mb-3 text-lg font-semibold text-slate-800">История решений</h2>
        {(review.audit_history || []).length ? (
          <ul className="space-y-3 text-sm text-slate-700">
            {review.audit_history.map((item) => (
              <li key={item.id} className="rounded-2xl bg-slate-50 px-4 py-3">
                <p className="font-medium">
                  {ACTION_LABELS[item.action] || item.action} · {item.moderator_name || item.moderator_id}
                </p>
                <p className="text-slate-500">{formatDateTime(item.created_at)}</p>
                {item.comment ? <p className="mt-1">{item.comment}</p> : null}
                {item.evidence_reviewed?.length ? (
                  <p className="mt-1 text-xs text-slate-400">
                    Просмотрено: {item.evidence_reviewed.join(', ')}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-slate-500">Решений ещё не было</p>
        )}
      </section>
      {(review.moderation_logs || []).length > 0 && (
        <section className="rounded-3xl bg-white p-6 shadow-md">
          <h2 className="mb-3 text-lg font-semibold text-slate-800">Журнал модерации карточки</h2>
          <ul className="space-y-2 text-sm text-slate-700">
            {review.moderation_logs.map((log) => (
              <li key={log.id}>
                {log.action} · {log.moderator_name} · {formatDateTime(log.created_at)}
                {log.comment ? ` · ${log.comment}` : ''}
              </li>
            ))}
          </ul>
        </section>
      )}
      {review.allowed_actions?.length > 0 && (
        <section className="rounded-3xl bg-white p-6 shadow-md">
          <h2 className="mb-3 text-lg font-semibold text-slate-800">Решение</h2>
          {message ? <p className="mb-3 text-sm text-teal-700">{message}</p> : null}
          {error ? <p className="mb-3 text-sm text-red-600">{error}</p> : null}
          <ModeratorCommentFields
            revisionComment={revisionComment}
            onRevisionChange={setRevisionComment}
            internalComment={internalComment}
            onInternalChange={setInternalComment}
          />
          <div className="mt-4 flex flex-wrap gap-3">
            {review.allowed_actions.map((action) => (
              <button
                key={action}
                type="button"
                disabled={loading}
                onClick={() => runAction(action)}
                className="rounded-2xl bg-teal-500 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
              >
                {ACTION_LABELS[ACTION_PATHS[action]] || action}
              </button>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
