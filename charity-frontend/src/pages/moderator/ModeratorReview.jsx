import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  approveCard,
  fetchModerationCard,
  fetchCardHistory,
  fetchCardTrustStatus,
  rejectCard,
  rejectDocument,
  requestCardRevision,
  requestDocumentRevision,
  verifyDocument,
  mediaUrl,
} from '../../api/client'
import EscrowBlock from '../../components/EscrowBlock'
import CardTimeline from '../../components/CardTimeline'
import ModeratorCommentFields, { CommentHistory } from '../../components/ModeratorCommentFields'
import { DocumentOriginalPreview, documentTypeLabel } from '../../components/PublicDocumentList'
import TrustBadges from '../../components/TrustBadges'
import { formatDate, formatMoney, statusLabel } from '../../utils/format'

export default function ModeratorReview() {
  const { id } = useParams()
  const [card, setCard] = useState(null)
  const [history, setHistory] = useState([])
  const [trustStatus, setTrustStatus] = useState(null)
  const [revisionComment, setRevisionComment] = useState('')
  const [internalComment, setInternalComment] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function loadCard() {
    fetchModerationCard(id).then(setCard).catch(() => setCard(null))
    fetchCardHistory(id).then(setHistory).catch(() => setHistory([]))
    fetchCardTrustStatus(id).then(setTrustStatus).catch(() => setTrustStatus(null))
  }

  useEffect(() => {
    loadCard()
  }, [id])

  const showEscrow = card && ['active', 'completed', 'deceased', 'redistribution'].includes(card.status)

  async function runAction(action) {
    setError('')
    setMessage('')
    setLoading(true)
    try {
      let result
      if (action === 'approve') result = await approveCard(id, revisionComment)
      if (action === 'reject') result = await rejectCard(id, revisionComment)
      if (action === 'revision') result = await requestCardRevision(id, revisionComment, internalComment)
      setCard(result)
      setMessage('Действие выполнено успешно')
      setRevisionComment('')
      setInternalComment('')
    } catch (err) {
      setError(err.data?.detail || err.data?.comment?.[0] || 'Ошибка выполнения действия')
    } finally {
      setLoading(false)
    }
  }

  async function handleDocumentAction(documentId, action) {
    try {
      if (action === 'verify') {
        await verifyDocument(documentId, {
          comment: revisionComment || '',
          has_confidential: true,
        })
      } else if (action === 'revision') {
        if (!revisionComment.trim()) {
          setError('Укажите, что нужно исправить в документе')
          return
        }
        await requestDocumentRevision(documentId, revisionComment, internalComment)
      } else {
        if (!revisionComment.trim()) {
          setError('Комментарий обязателен при отклонении документа')
          return
        }
        await rejectDocument(documentId, revisionComment)
      }
      loadCard()
    } catch (err) {
      setError(err.data?.detail || err.data?.revision_comment || 'Ошибка проверки документа')
    }
  }

  if (!card) {
    return <div className="rounded-3xl bg-white p-8 text-slate-500 shadow-md">Загрузка...</div>
  }

  const photo = mediaUrl(card.photo_url)

  return (
    <div className="space-y-6">
      <Link to="/moderator" className="text-sm font-medium text-teal-600 hover:underline">
        ← Назад к списку
      </Link>

      <section className="rounded-3xl bg-white p-6 shadow-md">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-bold text-slate-800">{card.full_name}</h1>
          <div className="flex flex-wrap items-center gap-2">
            {card.needs_extra_review && (
              <span className="rounded-full bg-amber-100 px-4 py-2 text-sm font-semibold text-amber-800">
                Усиленная проверка
              </span>
            )}
            {card.duplicate_suspected && (
              <span className="rounded-full bg-rose-100 px-4 py-2 text-sm font-semibold text-rose-800">
                Возможный дубль
              </span>
            )}
            <span className="rounded-full bg-mint-100 px-4 py-2 text-sm font-medium text-teal-600">
              {statusLabel(card.status)}
            </span>
          </div>
        </div>
        {card.needs_extra_review && (
          <p className="mb-4 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-900">
            Антифрод-система отметила этот сбор для усиленной проверки. Проверьте документы и данные особенно внимательно.
          </p>
        )}
        {card.duplicate_suspected && (
          <div className="mb-4 rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-900">
            <p className="font-semibold">Сигналы дублей</p>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              {(card.duplicate_signals || []).map((item) => (
                <li key={item.code || item.message}>
                  {item.message || item.code}
                  {(item.matched_card_ids || []).length
                    ? ` · карточки ${(item.matched_card_ids || []).join(', ')}`
                    : ''}
                </li>
              ))}
            </ul>
          </div>
        )}
        <div className="grid gap-6 lg:grid-cols-2">
          <div>
            {photo && (
              <img src={photo} alt={card.full_name} className="mb-4 w-full rounded-2xl object-cover" />
            )}
            <div className="grid gap-2 text-sm text-slate-700">
              <p><span className="font-medium">Диагноз:</span> {card.diagnosis}</p>
              <p><span className="font-medium">Город:</span> {card.city}</p>
              <p><span className="font-medium">Поликлиника:</span> {card.clinic || '—'}</p>
              <p><span className="font-medium">Возраст:</span> {card.age || '—'}</p>
              <p><span className="font-medium">Сумма:</span> {formatMoney(card.target_amount)}</p>
              <p><span className="font-medium">Дата окончания:</span> {formatDate(card.end_date)}</p>
              <p><span className="font-medium">Автор:</span> {card.author_email}</p>
            </div>
          </div>
          <div className="space-y-3 rounded-2xl bg-red-50 p-4 text-sm">
            <h2 className="font-semibold text-slate-800">Конфиденциальные данные</h2>
            <p><span className="font-medium">ИИН:</span> {card.iin}</p>
            <p><span className="font-medium">Удостоверение:</span> {card.document_number}</p>
            <p><span className="font-medium">Телефон:</span> {card.contact_phone}</p>
            <p><span className="font-medium">Email:</span> {card.contact_email || '—'}</p>
          </div>
        </div>
        <p className="mt-4 text-slate-700">{card.description}</p>
      </section>

      <TrustBadges trustStatus={trustStatus || card.trust_status} />
      <CardTimeline events={history} staff />

      <section className="rounded-3xl bg-white p-6 shadow-md">
        <h2 className="mb-4 text-xl font-semibold text-slate-800">Документы</h2>
        <div className="space-y-4">
          {(card.documents || []).map((doc) => (
            <div key={doc.id} className="rounded-2xl border border-sky-100 p-4">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-medium text-slate-800">
                    {documentTypeLabel(doc.document_type)} · {doc.file_name}
                  </p>
                  <p className="text-sm text-slate-500">
                    {doc.file_type} · {statusLabel(doc.verification_status || doc.status)} · версия {doc.version_number || 1}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => handleDocumentAction(doc.id, 'verify')}
                    className="rounded-xl bg-teal-500 px-3 py-2 text-sm text-white"
                  >
                    Проверен
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDocumentAction(doc.id, 'revision')}
                    className="rounded-xl bg-amber-500 px-3 py-2 text-sm text-white"
                  >
                    На доработку
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDocumentAction(doc.id, 'reject')}
                    className="rounded-xl bg-red-500 px-3 py-2 text-sm text-white"
                  >
                    Отклонить
                  </button>
                </div>
              </div>
              <DocumentOriginalPreview documentId={doc.id} fileType={doc.file_type} fileName={doc.file_name} />
            </div>
          ))}
        </div>
      </section>

      {showEscrow && card.escrow_balance !== undefined && (
        <EscrowBlock card={card} />
      )}

      {card.comments?.length > 0 && (
        <section className="rounded-3xl bg-white p-6 shadow-md">
          <h2 className="mb-4 text-xl font-semibold text-slate-800">Комментарии модерации</h2>
          <CommentHistory comments={card.comments} />
        </section>
      )}

      {card.moderation_logs?.length > 0 && (
        <section className="rounded-3xl bg-white p-6 shadow-md">
          <h2 className="mb-4 text-xl font-semibold text-slate-800">История модерации</h2>
          <div className="space-y-2">
            {card.moderation_logs.map((log) => (
              <div key={log.id} className="rounded-2xl bg-sky-50 p-3 text-sm">
                <p className="font-medium text-slate-800">{log.action}</p>
                <p className="text-slate-600">{log.comment || '—'}</p>
                <p className="text-xs text-slate-400">{formatDate(log.created_at)}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {(card.status === 'pending_moderation' || card.status === 'manual_review') && (
        <section className="rounded-3xl bg-white p-6 shadow-md">
          <h2 className="mb-4 text-xl font-semibold text-slate-800">Решение модератора</h2>
          <ModeratorCommentFields
            revisionComment={revisionComment}
            onRevisionChange={setRevisionComment}
            internalComment={internalComment}
            onInternalChange={setInternalComment}
          />
          {error && <p className="mb-3 mt-3 text-sm text-red-600">{error}</p>}
          {message && <p className="mb-3 text-sm text-teal-700">{message}</p>}
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              disabled={loading}
              onClick={() => runAction('approve')}
              className="rounded-2xl bg-teal-500 px-5 py-3 font-semibold text-white hover:bg-teal-600"
            >
              Одобрить
            </button>
            <button
              type="button"
              disabled={loading}
              onClick={() => runAction('revision')}
              className="rounded-2xl bg-amber-500 px-5 py-3 font-semibold text-white hover:bg-amber-600"
            >
              На доработку
            </button>
            <button
              type="button"
              disabled={loading}
              onClick={() => runAction('reject')}
              className="rounded-2xl bg-red-500 px-5 py-3 font-semibold text-white hover:bg-red-600"
            >
              Отклонить
            </button>
          </div>
        </section>
      )}
    </div>
  )
}
