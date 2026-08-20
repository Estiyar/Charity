import { useEffect, useState } from 'react'
import { fetchDocumentOriginalBlob, mediaUrl } from '../api/client'
import { formatDate, statusLabel } from '../utils/format'

const TYPE_LABELS = {
  medical: 'Медицинский',
  diagnosis: 'Диагноз',
  clinic: 'Клиника',
  identity: 'Удостоверение',
  representation: 'Представительство',
  other: 'Другое',
}

export function documentTypeLabel(value) {
  return TYPE_LABELS[value] || value || 'Документ'
}

export function DocumentOriginalPreview({ documentId, fileType, fileName }) {
  const [fileUrl, setFileUrl] = useState(null)

  useEffect(() => {
    let current = null
    fetchDocumentOriginalBlob(documentId)
      .then((url) => {
        current = url
        setFileUrl(url)
      })
      .catch(() => setFileUrl(null))
    return () => {
      if (current) URL.revokeObjectURL(current)
    }
  }, [documentId])

  if (!fileUrl) {
    return <p className="text-sm text-slate-500">Оригинал недоступен.</p>
  }
  if (fileType === 'pdf') {
    return <iframe title={fileName} src={fileUrl} className="h-64 w-full rounded-xl border" />
  }
  return (
    <a href={fileUrl} target="_blank" rel="noreferrer" className="text-sm text-teal-600 hover:underline">
      Открыть оригинал
    </a>
  )
}

export default function PublicDocumentList({ documents }) {
  const items = documents || []
  return (
    <section className="rounded-3xl bg-white p-6 shadow-md">
      <h2 className="text-xl font-semibold text-slate-800">Подтверждающие документы</h2>
      {items.length ? (
        <ul className="mt-4 space-y-3">
          {items.map((doc) => (
            <li key={doc.id} className="rounded-2xl bg-sky-50 px-4 py-3 text-sm text-slate-700">
              <p className="font-medium text-slate-800">{documentTypeLabel(doc.document_type)}</p>
              <p className="text-xs text-slate-500">
                {doc.issuer || 'Организация скрыта'} · {formatDate(doc.issued_at)} · {statusLabel(doc.verification_status)}
              </p>
              {doc.public_file_url ? (
                <a
                  href={mediaUrl(doc.public_file_url)}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 inline-block text-sm text-teal-600 hover:underline"
                >
                  Публичная копия
                </a>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm text-slate-500">Публичные копии документов пока недоступны.</p>
      )}
    </section>
  )
}
