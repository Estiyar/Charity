import { redistributionCaseLabel, redistributionDecisionLabel, formatDate } from '../utils/format'

export default function RedistributionHistory({ data }) {
  const decisions = data?.decisions || []

  return (
    <section className="rounded-3xl bg-white p-6 shadow-md">
      <h2 className="text-xl font-semibold text-slate-800">История перераспределения</h2>
      {data?.case && (
        <p className="mt-2 text-sm text-slate-600">
          Случай: {redistributionCaseLabel(data.case)}
        </p>
      )}
      {!decisions.length ? (
        <p className="mt-4 text-sm text-slate-500">Решений по перераспределению пока нет.</p>
      ) : (
        <div className="mt-4 space-y-3">
          {decisions.map((decision) => (
            <div key={decision.id} className="rounded-2xl bg-sky-50 p-4 text-sm">
              <p className="font-medium text-slate-800">
                {decision.decision_type_label || redistributionDecisionLabel(decision.decision_type)}
              </p>
              {decision.target_card_name && (
                <p className="text-slate-600">Целевой сбор: {decision.target_card_name}</p>
              )}
              {decision.comment && <p className="text-slate-600">{decision.comment}</p>}
              <p className="text-xs text-slate-400">
                {decision.created_by_name || 'Модератор'} · {formatDate(decision.created_at)}
              </p>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
