import { useEffect, useState } from 'react'
import { fetchCards } from '../api/client'
import CardGrid from '../components/CardGrid'
import Filters, { initialFilters } from '../components/Filters'

export default function Catalog() {
  const [filters, setFilters] = useState(initialFilters)
  const [cards, setCards] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    const params = { ...filters }
    if (params.search) {
      params.search = params.search
    }
    fetchCards(params)
      .then((data) => setCards(data.results || []))
      .catch(() => setCards([]))
      .finally(() => setLoading(false))
  }, [filters])

  return (
    <div className="mx-auto max-w-7xl space-y-8 px-4 py-10">
      <div>
        <h1 className="text-3xl font-bold text-slate-800">Каталог сборов</h1>
        <p className="mt-2 text-slate-600">
          Публичные сборы со всеми полями, фильтрами и прогрессом сбора.
        </p>
      </div>
      <Filters
        filters={filters}
        onChange={setFilters}
        onReset={() => setFilters(initialFilters)}
      />
      {loading ? (
        <div className="rounded-3xl bg-white p-10 text-center text-slate-500 shadow-md">
          Загрузка...
        </div>
      ) : (
        <CardGrid cards={cards} />
      )}
    </div>
  )
}
