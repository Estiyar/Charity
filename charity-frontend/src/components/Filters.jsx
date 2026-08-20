const STATUS_OPTIONS = [
  { value: '', label: 'Все статусы' },
  { value: 'active', label: 'Активен' },
  { value: 'completed', label: 'Завершён' },
  { value: 'redistribution', label: 'Перераспределение' },
]

const ORDER_OPTIONS = [
  { value: '-created_at', label: 'Сначала новые' },
  { value: '-target_amount', label: 'Сумма цели: по убыванию' },
  { value: 'target_amount', label: 'Сумма цели: по возрастанию' },
  { value: '-collected_amount', label: 'Собрано: по убыванию' },
  { value: 'collected_amount', label: 'Собрано: по возрастанию' },
  { value: '-progress', label: 'Прогресс: по убыванию' },
  { value: 'progress', label: 'Прогресс: по возрастанию' },
  { value: '-age', label: 'Возраст: по убыванию' },
  { value: 'age', label: 'Возраст: по возрастанию' },
  { value: 'end_date', label: 'Окончание: сначала ближайшие' },
  { value: '-end_date', label: 'Окончание: сначала поздние' },
]

const initialFilters = {
  city: '',
  diagnosis: '',
  status: '',
  end_date_from: '',
  end_date_to: '',
  target_amount_min: '',
  target_amount_max: '',
  age_min: '',
  age_max: '',
  ordering: '-created_at',
  search: '',
}

export { initialFilters }

function FilterInput({ className = '', ...props }) {
  return (
    <input
      {...props}
      className={`rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500 ${className}`}
    />
  )
}

export default function Filters({ filters, references = {}, onChange, onReset }) {
  const update = (field, value) => onChange({ ...filters, [field]: value })
  const cities = references.cities || []
  const diagnoses = references.diagnoses || []

  return (
    <section className="rounded-3xl bg-white p-4 shadow-md sm:p-6">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-lg font-semibold text-slate-800">Фильтры</h2>
        <button
          type="button"
          onClick={onReset}
          className="rounded-full border border-sky-200 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-sky-50"
        >
          Сбросить фильтры
        </button>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <FilterInput
          type="text"
          placeholder="Поиск по ФИО, диагнозу, городу или описанию"
          value={filters.search}
          onChange={(e) => update('search', e.target.value)}
          className="sm:col-span-2 lg:col-span-3 xl:col-span-4"
        />
        <FilterInput
          type="text"
          list="catalog-cities"
          placeholder="Город"
          value={filters.city}
          onChange={(e) => update('city', e.target.value)}
        />
        <FilterInput
          type="text"
          list="catalog-diagnoses"
          placeholder="Диагноз"
          value={filters.diagnosis}
          onChange={(e) => update('diagnosis', e.target.value)}
        />
        <select
          value={filters.status}
          onChange={(e) => update('status', e.target.value)}
          className="rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
        >
          {STATUS_OPTIONS.map((option) => (
            <option key={option.value || 'all'} value={option.value}>{option.label}</option>
          ))}
        </select>
        <select
          value={filters.ordering}
          onChange={(e) => update('ordering', e.target.value)}
          className="rounded-2xl border border-sky-100 px-4 py-3 text-sm outline-none focus:border-teal-500"
        >
          {ORDER_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
        <FilterInput type="date" value={filters.end_date_from} onChange={(e) => update('end_date_from', e.target.value)} />
        <FilterInput type="date" value={filters.end_date_to} onChange={(e) => update('end_date_to', e.target.value)} />
        <FilterInput type="number" placeholder="Сумма от" value={filters.target_amount_min} onChange={(e) => update('target_amount_min', e.target.value)} />
        <FilterInput type="number" placeholder="Сумма до" value={filters.target_amount_max} onChange={(e) => update('target_amount_max', e.target.value)} />
        <FilterInput type="number" placeholder="Возраст от" value={filters.age_min} onChange={(e) => update('age_min', e.target.value)} />
        <FilterInput type="number" placeholder="Возраст до" value={filters.age_max} onChange={(e) => update('age_max', e.target.value)} />
      </div>
      <datalist id="catalog-cities">
        {cities.map((city) => (
          <option key={city} value={city} />
        ))}
      </datalist>
      <datalist id="catalog-diagnoses">
        {diagnoses.map((diagnosis) => (
          <option key={diagnosis} value={diagnosis} />
        ))}
      </datalist>
    </section>
  )
}
