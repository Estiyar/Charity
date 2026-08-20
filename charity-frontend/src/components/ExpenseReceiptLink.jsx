import { useState } from 'react'
import { fetchExpenseOriginalBlob, mediaUrl } from '../api/client'

function isPrivateOriginal(path) {
  return typeof path === 'string' && path.includes('/original/')
}

export default function ExpenseReceiptLink({ expense, label = 'Открыть' }) {
  const [loading, setLoading] = useState(false)
  const publicUrl = mediaUrl(expense.public_receipt_url)
  const privatePath = expense.original_url || (isPrivateOriginal(expense.document) ? expense.document : null)
  const publicDocument = !privatePath && expense.document ? mediaUrl(expense.document) : null

  async function openPrivate() {
    setLoading(true)
    try {
      const blobUrl = await fetchExpenseOriginalBlob(expense.id)
      window.open(blobUrl, '_blank', 'noopener,noreferrer')
    } finally {
      setLoading(false)
    }
  }

  if (privatePath) {
    return (
      <button
        type="button"
        onClick={openPrivate}
        disabled={loading}
        className="text-teal-600 hover:underline disabled:opacity-60"
      >
        {loading ? 'Загрузка...' : label}
      </button>
    )
  }
  if (publicUrl) {
    return (
      <a href={publicUrl} target="_blank" rel="noreferrer" className="text-teal-600 hover:underline">
        {label}
      </a>
    )
  }
  if (publicDocument) {
    return (
      <a href={publicDocument} target="_blank" rel="noreferrer" className="text-teal-600 hover:underline">
        {label}
      </a>
    )
  }
  return '—'
}
