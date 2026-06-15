import { formatMoney } from '../utils/format'

export default function EscrowBlock({ card }) {
  return (
    <section className="rounded-3xl bg-white p-6 shadow-md">
      <h2 className="text-xl font-semibold text-slate-800">Эскроу-счёт</h2>
      <p className="mt-2 text-sm text-slate-600">
        Средства учитываются отдельно по каждой карточке.
      </p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-2xl bg-sky-50 p-4">
          <p className="text-xs text-slate-500">Поступило</p>
          <p className="text-lg font-semibold text-slate-800">{formatMoney(card.escrow_received)}</p>
        </div>
        <div className="rounded-2xl bg-sky-50 p-4">
          <p className="text-xs text-slate-500">Доступно</p>
          <p className="text-lg font-semibold text-slate-800">{formatMoney(card.escrow_available)}</p>
        </div>
        <div className="rounded-2xl bg-sky-50 p-4">
          <p className="text-xs text-slate-500">Потрачено</p>
          <p className="text-lg font-semibold text-slate-800">{formatMoney(card.escrow_spent)}</p>
        </div>
        <div className="rounded-2xl bg-sky-50 p-4">
          <p className="text-xs text-slate-500">На проверке</p>
          <p className="text-lg font-semibold text-slate-800">{formatMoney(card.escrow_pending)}</p>
        </div>
      </div>
      <p className="mt-4 text-sm text-slate-600">
        Остаток: <span className="font-semibold text-slate-800">{formatMoney(card.escrow_balance)}</span>
      </p>
    </section>
  )
}
