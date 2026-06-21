import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  approveCard,
  fetchModerationCard,
  rejectCard,
  rejectDocument,
  requestCardRevision,
  verifyDocument,
  mediaUrl,
} from '../../api/client'
import EscrowBlock from '../../components/EscrowBlock'
import { formatDate, formatMoney, statusLabel } from '../../utils/format'

export default function ModeratorReview() {
  const { id } = useParams()
  const [card, setCard] = useState(null)
  const [comment, setComment] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function loadCard() {
    fetchModerationCard(id).then(setCard).catch(() => setCard(null))
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
      if (action === 'approve') result = await approveCard(id, comment)
      if (action === 'reject') result = await rejectCard(id, comment)
      if (action === 'revision') result = await requestCardRevision(id, comment)
      setCard(result)
      setMessage('Действие выполнено успешно')
      setComment('')
    } catch (err) {
      setError(err.data?.detail || err.data?.comment?.[0] || 'Ошибка выполнения действия')
    } finally {
      setLoading(false)
    }
  }

  async function handleDocumentAction(documentId, action) {
    const docComment = prompt(action === 'verify' ? 'Комментарий (необязательно)' : 'Комментарий (обязательно)')
    if (action === 'reject' && !docComment?.trim()) return
    try {
      if (action === 'verify') {
        await verifyDocument(documentId, {
          comment: docComment || '',
          has_confidential: true,
        })
      } else {
        await rejectDocument(documentId, docComment)
      }
      loadCard()
    } catch (err) {
      setError(err.data?.detail || 'Ошибка проверки документа')
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
          <span className="rounded-full bg-mint-100 px-4 py-2 text-sm font-medium text-teal-600">
            {statusLabel(card.status)}
          </span>
        </div>
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

      <section className="rounded-3xl bg-white p-6 shadow-md">
        <h2 className="mb-4 text-xl font-semibold text-slate-800">Документы</h2>
        <div className="space-y-4">
          {(card.documents || []).map((doc) => {
            const fileUrl = mediaUrl(doc.file_url)
            return (
              <div key={doc.id} className="rounded-2xl border border-sky-100 p-4">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="font-medium text-slate-800">{doc.file_name}</p>
                    <p className="text-sm text-slate-500">{doc.file_type} · {statusLabel(doc.status)}</p>
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
                      onClick={() => handleDocumentAction(doc.id, 'reject')}
                      className="rounded-xl bg-red-500 px-3 py-2 text-sm text-white"
                    >
                      Отклонить
                    </button>
                  </div>
                </div>
                {doc.file_type === 'pdf' && fileUrl && (
                  <iframe title={doc.file_name} src={fileUrl} className="h-64 w-full rounded-xl border" />
                )}
                {doc.file_type !== 'pdf' && fileUrl && (
                  <a href={fileUrl} target="_blank" rel="noreferrer" className="text-sm text-teal-600 hover:underline">
                    Открыть файл
                  </a>
                )}
              </div>
            )
          })}
        </div>
      </section>

      {showEscrow && card.escrow_balance !== undefined && (
        <EscrowBlock card={card} />
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

      {card.status === 'pending_moderation' && (
        <section className="rounded-3xl bg-white p-6 shadow-md">
          <h2 className="mb-4 text-xl font-semibold text-slate-800">Решение модератора</h2>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Комментарий (обязателен при отклонении и доработке)"
            className="mb-4 w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
            rows={4}
          />
          {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
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
