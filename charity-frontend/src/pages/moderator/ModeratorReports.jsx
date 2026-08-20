import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchModerationReports, resolveModerationReport } from '../../api/client'
import { formatDate } from '../../utils/format'

const categoryLabels = {
  suspected_fraud: 'Мошенничество',
  incorrect_information: 'Неверная информация',
  stolen_photos: 'Чужие фото',
  outdated_fundraiser: 'Устаревший сбор',
  document_issue: 'Документы',
  other: 'Другое',
}

export default function ModeratorReports() {
  const [reports, setReports] = useState([])
  const [error, setError] = useState('')
  const [resolution, setResolution] = useState({})
  const [busyId, setBusyId] = useState(null)

  function loadReports() {
    fetchModerationReports()
      .then(setReports)
      .catch(() => setError('Не удалось загрузить жалобы.'))
  }

  useEffect(() => {
    loadReports()
  }, [])

  async function handleResolve(reportId, status) {
    const text = (resolution[reportId] || '').trim()
    if (text.length < 3) {
      setError('Укажите текст решения.')
      return
    }
    setBusyId(reportId)
    setError('')
    try {
      await resolveModerationReport(reportId, { status, resolution: text })
      loadReports()
    } catch (err) {
      setError(err.message || 'Не удалось сохранить решение.')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-800">Жалобы пользователей</h1>
        <p className="mt-2 text-slate-600">Очередь модерации по публичным жалобам на сборы.</p>
      </div>
      {error ? <p className="text-sm text-rose-600">{error}</p> : null}
      {reports.length ? (
        <div className="space-y-4">
          {reports.map((report) => (
            <article key={report.id} className="rounded-3xl bg-white p-6 shadow-md">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm text-slate-500">{formatDate(report.created_at)}</p>
                  <h2 className="text-lg font-semibold text-slate-800">
                    Сбор #{report.card_id} · {categoryLabels[report.category] || report.category}
                  </h2>
                  <p className="mt-2 text-slate-700">{report.description}</p>
                </div>
                <Link
                  to={`/moderator/cards/${report.card_id}`}
                  className="rounded-2xl bg-sky-100 px-4 py-2 text-sm font-medium text-slate-700"
                >
                  Открыть сбор
                </Link>
              </div>
              <textarea
                value={resolution[report.id] || ''}
                onChange={(event) =>
                  setResolution((current) => ({ ...current, [report.id]: event.target.value }))
                }
                rows={3}
                placeholder="Решение модератора"
                className="mt-4 w-full rounded-2xl border border-sky-100 px-4 py-3 text-sm"
              />
              <div className="mt-3 flex flex-wrap gap-3">
                <button
                  type="button"
                  disabled={busyId === report.id}
                  onClick={() => handleResolve(report.id, 'resolved')}
                  className="rounded-2xl bg-teal-500 px-4 py-2 text-sm font-semibold text-white"
                >
                  Подтвердить
                </button>
                <button
                  type="button"
                  disabled={busyId === report.id}
                  onClick={() => handleResolve(report.id, 'dismissed')}
                  className="rounded-2xl bg-slate-200 px-4 py-2 text-sm font-semibold text-slate-700"
                >
                  Отклонить
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <p className="rounded-3xl bg-white p-6 text-slate-600 shadow-md">Открытых жалоб нет.</p>
      )}
    </div>
  )
}
