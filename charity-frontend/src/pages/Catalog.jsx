import CardGrid from '../components/CardGrid'
import CatalogPagination from '../components/CatalogPagination'
import CatalogTable from '../components/CatalogTable'
import Filters from '../components/Filters'
import { useCatalog } from '../hooks/useCatalog'

function ViewSwitch({ view, onChange }) {
  return (
    <div className="flex rounded-full border border-sky-200 bg-white p-1">
      <button
        type="button"
        onClick={() => onChange('cards')}
        className={`rounded-full px-4 py-2 text-sm font-medium transition ${
          view === 'cards' ? 'bg-teal-500 text-white' : 'text-slate-600 hover:bg-sky-50'
        }`}
      >
        Карточки
      </button>
      <button
        type="button"
        onClick={() => onChange('table')}
        className={`rounded-full px-4 py-2 text-sm font-medium transition ${
          view === 'table' ? 'bg-teal-500 text-white' : 'text-slate-600 hover:bg-sky-50'
        }`}
      >
        Таблица
      </button>
    </div>
  )
}

export default function Catalog() {
  const catalog = useCatalog()

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:space-y-8 sm:py-10">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-800">Каталог сборов</h1>
          <p className="mt-2 text-slate-600">
            Публичные сборы с фильтрами, сортировкой и пагинацией на стороне сервера.
          </p>
        </div>
        <ViewSwitch view={catalog.view} onChange={catalog.setView} />
      </div>
      <Filters
        filters={catalog.filters}
        references={catalog.references}
        onChange={catalog.changeFilters}
        onReset={catalog.resetFilters}
      />
      {catalog.loading ? (
        <div className="rounded-3xl bg-white p-10 text-center text-slate-500 shadow-md">
          Загрузка...
        </div>
      ) : catalog.error ? (
        <div className="rounded-3xl bg-white p-10 text-center shadow-md">
          <p className="text-slate-700">{catalog.error}</p>
          <button
            type="button"
            onClick={catalog.reload}
            className="mt-4 rounded-full bg-teal-500 px-5 py-2 text-sm font-semibold text-white hover:bg-teal-600"
          >
            Повторить
          </button>
        </div>
      ) : catalog.view === 'table' ? (
        <CatalogTable cards={catalog.results} />
      ) : (
        <CardGrid cards={catalog.results} />
      )}
      {!catalog.loading && !catalog.error && (
        <CatalogPagination
          page={catalog.page}
          pageCount={catalog.pageCount}
          count={catalog.count}
          onPageChange={catalog.setPage}
        />
      )}
    </div>
  )
}
