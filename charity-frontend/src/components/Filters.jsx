const STATUS_OPTIONS = [
  { value: '', label: 'Все статусы' },
  { value: 'active', label: 'Активен' },
  { value: 'completed', label: 'Завершён' },
  { value: 'redistribution', label: 'Перераспределение' },
]

const initialFilters = {
  city: '',
  diagnosis: '',
  status: '',
  end_date_from: '',
  end_date_to: '',
  target_amount_min: '',
  target_amount_max: '',
  search: '',
}

export { initialFilters }

export default function Filters({ filters, onChange, onReset }) {
  const update = (field, value) => onChange({ ...filters, [field]: value })

  return (
    <section className="rounded-3xl bg-white p-6 shadow-md">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-800">Фильтры</h2>
        <button
          type="button"
          onClick={onReset}
          className="rounded-full border border-sky-200 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-sky-50"
        >
          Сбросить фильтры
        </button>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        <input
          type="text"
          placeholder="Поиск по ФИО или ключевому слову"
          value={filters.search}
          onChange={(e) => update('search', e.target.value)}
          className="rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500 lg:col-span-3"
        />
        <input
          type="text"
          placeholder="Город"
          value={filters.city}
          onChange={(e) => update('city', e.target.value)}
          className="rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
        />
        <input
          type="text"
          placeholder="Диагноз"
          value={filters.diagnosis}
          onChange={(e) => update('diagnosis', e.target.value)}
          className="rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
        />
        <select
          value={filters.status}
          onChange={(e) => update('status', e.target.value)}
          className="rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
        >
          {STATUS_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
        <input
          type="date"
          value={filters.end_date_from}
          onChange={(e) => update('end_date_from', e.target.value)}
          className="rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
        />
        <input
          type="date"
          value={filters.end_date_to}
          onChange={(e) => update('end_date_to', e.target.value)}
          className="rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
        />
        <input
          type="number"
          placeholder="Сумма от"
          value={filters.target_amount_min}
          onChange={(e) => update('target_amount_min', e.target.value)}
          className="rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
        />
        <input
          type="number"
          placeholder="Сумма до"
          value={filters.target_amount_max}
          onChange={(e) => update('target_amount_max', e.target.value)}
          className="rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
        />
      </div>
    </section>
  )
}
