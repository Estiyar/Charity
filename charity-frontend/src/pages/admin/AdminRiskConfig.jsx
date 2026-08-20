import { useEffect, useState } from 'react'
import { fetchAdminRiskConfig, updateAdminRiskConfig, fetchAdminRiskConfigHistory } from '../../api/client'
import { formatDate } from '../../utils/format'

function WeightEditor({ label, weights, onChange }) {
  return (
    <div>
      <h3 className="mb-2 text-lg font-semibold text-slate-800">{label}</h3>
      <div className="space-y-2">
        {Object.entries(weights).map(([key, value]) => (
          <label key={key} className="flex items-center justify-between rounded-2xl bg-sky-50 px-4 py-2 text-sm">
            <span className="font-mono text-slate-700">{key}</span>
            <input
              type="number"
              min={0}
              max={100}
              value={value}
              onChange={(event) => onChange({ ...weights, [key]: Number(event.target.value) })}
              className="w-20 rounded-xl border border-sky-200 px-2 py-1 text-center"
            />
          </label>
        ))}
      </div>
    </div>
  )
}

export default function AdminRiskConfig() {
  const [config, setConfig] = useState(null)
  const [history, setHistory] = useState([])
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [saving, setSaving] = useState(false)
  const [draft, setDraft] = useState(null)

  function load() {
    fetchAdminRiskConfig().then((data) => {
      setConfig(data)
      setDraft({
        factor_weights: { ...data.factor_weights },
        risk_thresholds: { ...data.risk_thresholds },
        business_limits: { ...data.business_limits },
      })
    }).catch(() => setError('Не удалось загрузить конфигурацию риска.'))
    fetchAdminRiskConfigHistory().then(setHistory).catch(() => setHistory([]))
  }

  useEffect(() => { load() }, [])

  async function handleSave() {
    setError('')
    setSuccess('')
    setSaving(true)
    try {
      const updated = await updateAdminRiskConfig(draft)
      setConfig(updated)
      setDraft({
        factor_weights: { ...updated.factor_weights },
        risk_thresholds: { ...updated.risk_thresholds },
        business_limits: { ...updated.business_limits },
      })
      setSuccess('Конфигурация обновлена.')
      fetchAdminRiskConfigHistory().then(setHistory).catch(() => {})
    } catch (err) {
      setError(err.message || 'Не удалось сохранить.')
    } finally {
      setSaving(false)
    }
  }

  if (!config || !draft) {
    return <div className="rounded-3xl bg-white p-8 text-slate-500 shadow-md">Загрузка...</div>
  }

  return (
    <div className="space-y-6">
      <section className="rounded-3xl bg-white p-6 shadow-md">
        <h1 className="mb-2 text-2xl font-semibold text-slate-800">Конфигурация рисков</h1>
        <p className="mb-4 text-sm text-slate-600">Версия: {config.version}</p>
        <div className="grid gap-6 lg:grid-cols-2">
          <WeightEditor
            label="Веса факторов риска"
            weights={draft.factor_weights}
            onChange={(updated) => setDraft((prev) => ({ ...prev, factor_weights: updated }))}
          />
          <div className="space-y-6">
            <WeightEditor
              label="Пороги уровней"
              weights={draft.risk_thresholds}
              onChange={(updated) => setDraft((prev) => ({ ...prev, risk_thresholds: updated }))}
            />
            <WeightEditor
              label="Бизнес-лимиты"
              weights={draft.business_limits}
              onChange={(updated) => setDraft((prev) => ({ ...prev, business_limits: updated }))}
            />
          </div>
        </div>
        {error ? <p className="mt-4 text-sm text-rose-600">{error}</p> : null}
        {success ? <p className="mt-4 text-sm text-teal-700">{success}</p> : null}
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="mt-4 rounded-2xl bg-teal-500 px-6 py-3 text-sm font-semibold text-white disabled:opacity-60"
        >
          {saving ? 'Сохранение…' : 'Сохранить'}
        </button>
      </section>
      <section className="rounded-3xl bg-white p-6 shadow-md">
        <h2 className="mb-4 text-xl font-semibold text-slate-800">История изменений</h2>
        {history.length ? (
          <div className="space-y-2">
            {history.map((entry) => (
              <div key={entry.id} className="rounded-2xl bg-sky-50 p-3 text-sm">
                <p className="font-medium text-slate-800">{entry.action}</p>
                <p className="text-slate-500">{entry.actor_name || '—'} · {formatDate(entry.created_at)}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">Изменений пока нет.</p>
        )}
      </section>
    </div>
  )
}
