export function formatMoney(value) {
  const amount = Number(value || 0)
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'KZT',
    maximumFractionDigits: 0,
  }).format(amount)
}

export function formatDate(value) {
  if (!value) return '—'
  return new Date(value).toLocaleDateString('ru-RU')
}

const STATUS_LABELS = {
  active: 'Активен',
  completed: 'Завершён',
  redistribution: 'Перераспределение',
  draft: 'Черновик',
  pending_moderation: 'На модерации',
  revision_required: 'На доработке',
  approved: 'Одобрен',
  rejected: 'Отклонён',
}

export function statusLabel(status) {
  return STATUS_LABELS[status] || status
}

const STATUS_BADGE_CLASSES = {
  draft: 'bg-slate-100 text-slate-700',
  pending_moderation: 'bg-amber-100 text-amber-800',
  revision_required: 'bg-orange-100 text-orange-800',
  approved: 'bg-sky-100 text-sky-800',
  active: 'bg-mint-100 text-teal-800',
  rejected: 'bg-red-100 text-red-700',
  completed: 'bg-indigo-100 text-indigo-800',
  deceased: 'bg-slate-200 text-slate-800',
  redistribution: 'bg-purple-100 text-purple-800',
  archived: 'bg-slate-100 text-slate-500',
}

export function statusBadgeClass(status) {
  return STATUS_BADGE_CLASSES[status] || 'bg-sky-50 text-slate-700'
}

const ROLE_LABELS = {
  donor: 'Донор',
  author: 'Автор сбора',
  moderator: 'Модератор',
  admin: 'Администратор',
}

export function roleLabel(role) {
  return ROLE_LABELS[role] || role
}

const EXPENSE_STATUS_LABELS = {
  pending: 'На проверке',
  approved: 'Подтверждён',
  rejected: 'Отклонён',
}

export function expenseStatusLabel(status) {
  return EXPENSE_STATUS_LABELS[status] || status
}

const REDISTRIBUTION_CASE_LABELS = {
  deceased: 'Получатель умер',
  completed_balance: 'Сбор завершён, есть остаток',
  no_documents: 'Нет подтверждённых документов расходов',
  unused_funds: 'Неиспользованные средства',
}

const REDISTRIBUTION_DECISION_LABELS = {
  refund: 'Вернуть донорам',
  transfer: 'Перераспределить на другой сбор',
  fund: 'Передать в общий фонд',
  hold: 'Оставить до завершения проверки',
}

export function redistributionCaseLabel(value) {
  return REDISTRIBUTION_CASE_LABELS[value] || value || '—'
}

export function redistributionDecisionLabel(value) {
  return REDISTRIBUTION_DECISION_LABELS[value] || value
}
