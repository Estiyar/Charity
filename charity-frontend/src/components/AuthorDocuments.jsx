import { useEffect, useState } from 'react'
import { fetchCardDocuments, fetchDocumentVersions, uploadDocument } from '../api/client'
import FileUploadField from './FileUploadField'
import { documentTypeLabel } from './PublicDocumentList'
import { formatDate, statusLabel } from '../utils/format'

const CAN_UPLOAD = new Set(['draft', 'revision_required', 'active'])

export default function AuthorDocuments({ cardId, cardStatus }) {
  const [documents, setDocuments] = useState([])
  const [versions, setVersions] = useState({})
  const [file, setFile] = useState(null)
  const [replaceId, setReplaceId] = useState('')
  const [issuer, setIssuer] = useState('')
  const [issuedAt, setIssuedAt] = useState('')
  const [error, setError] = useState('')

  function loadDocuments() {
    fetchCardDocuments(cardId).then(setDocuments).catch(() => setDocuments([]))
  }

  useEffect(() => {
    loadDocuments()
  }, [cardId])

  async function handleUpload() {
    if (!file) return
    setError('')
    const formData = new FormData()
    formData.append('file', file)
    formData.append('document_type', 'medical')
    if (issuer) formData.append('issuer', issuer)
    if (issuedAt) formData.append('issued_at', issuedAt)
    if (replaceId) formData.append('supersedes_document_id', replaceId)
    try {
      await uploadDocument(cardId, formData)
      setFile(null)
      setReplaceId('')
      loadDocuments()
    } catch (err) {
      setError(err.data?.file?.[0] || err.data?.detail || 'Не удалось загрузить документ.')
    }
  }

  function loadVersions(documentId) {
    fetchDocumentVersions(documentId)
      .then((items) => setVersions((current) => ({ ...current, [documentId]: items })))
      .catch(() => {})
  }

  return (
    <section className="rounded-3xl bg-white p-6 shadow-md">
      <h2 className="text-xl font-semibold text-slate-800">Медицинские документы</h2>
      <ul className="mt-4 space-y-3">
        {documents.map((doc) => (
          <li key={doc.id} className="rounded-2xl bg-sky-50 px-4 py-3 text-sm text-slate-700">
            <p className="font-medium text-slate-800">
              {documentTypeLabel(doc.document_type)} · версия {doc.version_number}
            </p>
            <p className="text-xs text-slate-500">
              {statusLabel(doc.verification_status)} · {doc.issuer || 'клиника не указана'} · {formatDate(doc.issued_at)}
            </p>
            {doc.moderator_comment ? (
              <p className="mt-2 rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-900">
                Что исправить: {doc.moderator_comment}
              </p>
            ) : null}
            <button type="button" onClick={() => loadVersions(doc.id)} className="mt-2 text-xs text-teal-700 hover:underline">
              История версий
            </button>
            {(versions[doc.id] || []).map((item) => (
              <p key={item.id} className="mt-1 text-xs text-slate-500">
                v{item.version_number} · {statusLabel(item.verification_status)} · {formatDate(item.created_at)}
              </p>
            ))}
          </li>
        ))}
      </ul>
      {CAN_UPLOAD.has(cardStatus) ? (
        <div className="mt-4 space-y-3">
          <FileUploadField
            id={`replace-doc-${cardId}`}
            accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
            label="Выбрать файл"
            files={file}
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
          <input
            value={issuer}
            onChange={(event) => setIssuer(event.target.value)}
            placeholder="Клиника / организация"
            className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm"
          />
          <input
            type="date"
            value={issuedAt}
            onChange={(event) => setIssuedAt(event.target.value)}
            className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm"
          />
          <select
            value={replaceId}
            onChange={(event) => setReplaceId(event.target.value)}
            className="w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm"
          >
            <option value="">Новый документ</option>
            {documents.map((doc) => (
              <option key={doc.id} value={doc.id}>
                Заменить: {documentTypeLabel(doc.document_type)} #{doc.id}
              </option>
            ))}
          </select>
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
          <button
            type="button"
            disabled={!file}
            onClick={handleUpload}
            className="rounded-2xl bg-teal-500 px-4 py-3 text-sm font-semibold text-white disabled:opacity-60"
          >
            {replaceId ? 'Загрузить новую версию' : 'Добавить документ'}
          </button>
        </div>
      ) : null}
    </section>
  )
}
