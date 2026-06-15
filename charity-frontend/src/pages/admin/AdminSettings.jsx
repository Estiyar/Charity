import { useEffect, useState } from 'react'
import { fetchAdminLogs, fetchAdminSettings, updateAdminSettings } from '../../api/client'
import { formatDate } from '../../utils/format'

const stubFields = [
  { key: 'demo_payment_enabled', label: 'Демо-платёж' },
  { key: 'bank_integration_stub', label: 'Интеграция с банком (заглушка)' },
  { key: 'escrow_integration_stub', label: 'Эскроу-интеграция (заглушка)' },
  { key: 'pdf_auto_check_stub', label: 'Авто-проверка PDF (заглушка)' },
  { key: 'notifications_stub', label: 'SMS/Email уведомления (заглушка)' },
  { key: 'egov_integration_stub', label: 'Интеграция eGov (заглушка)' },
]

export default function AdminSettings() {
  const [settings, setSettings] = useState(null)
  const [logs, setLogs] = useState([])

  useEffect(() => {
    fetchAdminSettings().then(setSettings)
    fetchAdminLogs().then(setLogs).catch(() => setLogs([]))
  }, [])

  async function toggleField(key) {
    const next = { ...settings, [key]: !settings[key] }
    const updated = await updateAdminSettings(next)
    setSettings(updated)
  }

  if (!settings) {
    return <div className="rounded-3xl bg-white p-8 text-slate-500 shadow-md">Загрузка...</div>
  }

  return (
    <div className="space-y-6">
      <section className="rounded-3xl bg-white p-6 shadow-md">
        <h1 className="mb-4 text-2xl font-semibold text-slate-800">Настройки платформы</h1>
        <p className="mb-4 text-sm text-slate-600">
          Заглушки раздела 33 ТЗ: интерфейс и логика готовы к подключению внешних сервисов.
        </p>
        <p className="mb-4 font-medium text-slate-800">{settings.site_name}</p>
        <div className="space-y-3">
          {stubFields.map((field) => (
            <label key={field.key} className="flex items-center justify-between rounded-2xl bg-sky-50 px-4 py-3 text-sm">
              <span>{field.label}</span>
              <input
                type="checkbox"
                checked={Boolean(settings[field.key])}
                onChange={() => toggleField(field.key)}
              />
            </label>
          ))}
        </div>
      </section>
      <section className="rounded-3xl bg-white p-6 shadow-md">
        <h2 className="mb-4 text-xl font-semibold text-slate-800">Системные логи модерации</h2>
        {!logs.length ? (
          <p className="text-sm text-slate-500">Логов пока нет.</p>
        ) : (
          <div className="space-y-2">
            {logs.map((log) => (
              <div key={log.id} className="rounded-2xl bg-sky-50 p-3 text-sm">
                <p className="font-medium text-slate-800">{log.action} · {log.card_name}</p>
                <p className="text-slate-500">{log.moderator_name} · {formatDate(log.created_at)}</p>
                {log.comment && <p className="text-slate-600">{log.comment}</p>}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
