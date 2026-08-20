export default function CatalogPagination({ page, pageCount, count, onPageChange }) {
  if (count === 0 || pageCount <= 1) return null

  return (
    <div className="flex flex-col items-center justify-between gap-3 rounded-3xl bg-white px-4 py-4 shadow-md sm:flex-row">
      <p className="text-sm text-slate-500">
        Страница {page} из {pageCount} · {count} сборов
      </p>
      <div className="flex gap-2">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          className="rounded-full border border-sky-200 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-sky-50 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Назад
        </button>
        <button
          type="button"
          disabled={page >= pageCount}
          onClick={() => onPageChange(page + 1)}
          className="rounded-full border border-sky-200 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-sky-50 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Вперёд
        </button>
      </div>
    </div>
  )
}
