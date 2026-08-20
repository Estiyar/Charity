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

export function formatDateTime(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const STATUS_LABELS = {
  active: 'Активен',
  completed: 'Завершён',
  redistribution: 'Перераспределение',
  draft: 'Черновик',
  pending_moderation: 'На модерации',
  manual_review: 'Ручная проверка',
  revision_required: 'На доработке',
  approved: 'Одобрен',
  rejected: 'Отклонён',
  suspended: 'Приостановлен',
  uploaded: 'Загружен',
  under_review: 'На проверке',
  verified: 'Проверен',
  expired: 'Истёк',
}

export function statusLabel(status) {
  return STATUS_LABELS[status] || status
}

const STATUS_BADGE_CLASSES = {
  draft: 'bg-slate-100 text-slate-700',
  pending_moderation: 'bg-amber-100 text-amber-800',
  manual_review: 'bg-rose-100 text-rose-800',
  revision_required: 'bg-orange-100 text-orange-800',
  approved: 'bg-sky-100 text-sky-800',
  active: 'bg-mint-100 text-teal-800',
  rejected: 'bg-red-100 text-red-700',
  suspended: 'bg-slate-200 text-slate-800',
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
  return ROLE_LABELS[role] || role || '—'
}

const USER_STATUS_LABELS = {
  active: 'Активен',
  unverified: 'Не подтверждён',
  ecp_verified: 'Подтверждён ЭЦП',
  manual_review: 'Ручная проверка',
  rejected: 'Отклонён',
  blocked: 'Заблокирован',
}

export function userStatusLabel(status) {
  return USER_STATUS_LABELS[status] || status || '—'
}

const ECP_STATUS_LABELS = {
  unverified: 'ЭЦП не подтверждена',
  verified: 'ЭЦП подтверждена',
  manual_review: 'ЭЦП на проверке',
}

export function ecpStatusLabel(status) {
  return ECP_STATUS_LABELS[status] || status || '—'
}

const RELATIONSHIP_LABELS = {
  self: 'Для себя',
  parent: 'Родитель',
  guardian: 'Опекун',
  representative: 'Представитель',
}

export function relationshipLabel(value) {
  return RELATIONSHIP_LABELS[value] || value || '—'
}

const REPRESENTATION_STATUS_LABELS = {
  pending: 'Ожидает подтверждения',
  verified: 'Подтверждено',
  rejected: 'Отклонено',
  manual_review: 'Ручная проверка',
}

export function representationStatusLabel(status) {
  return REPRESENTATION_STATUS_LABELS[status] || status || '—'
}

const REPRESENTATION_METHOD_LABELS = {
  ecp: 'ЭЦП получателя',
  document: 'Подтверждающий документ',
  external_source: 'Официальный источник',
  manual_review: 'Ручная проверка модератора',
}

export function representationMethodLabel(method) {
  return REPRESENTATION_METHOD_LABELS[method] || method || '—'
}

const PAYMENT_STATUS_LABELS = {
  pending: 'Ожидает оплаты',
  processing: 'Обработка',
  success: 'Оплачено',
  failed: 'Ошибка оплаты',
  canceled: 'Отменено',
}

export function paymentStatusLabel(status) {
  return PAYMENT_STATUS_LABELS[status] || status || '—'
}

const EXPENSE_STATUS_LABELS = {
  draft: 'Черновик',
  submitted: 'Отправлен',
  pending_review: 'На проверке',
  pending: 'На проверке',
  revision_required: 'На доработке',
  approved: 'Подтверждён',
  rejected: 'Отклонён',
  paid: 'Оплачен',
  canceled: 'Отменён',
}

export function expenseStatusLabel(status) {
  return EXPENSE_STATUS_LABELS[status] || status
}

const EXPENSE_CATEGORY_LABELS = {
  medicine: 'Лекарства',
  treatment: 'Лечение',
  clinic: 'Клиника',
  transport: 'Транспорт',
  living: 'Проживание',
  other: 'Другое',
}

export function expenseCategoryLabel(category) {
  return EXPENSE_CATEGORY_LABELS[category] || category || '—'
}

const INVOICE_STATUS_LABELS = {
  pending_verification: 'Ожидает проверки',
  verified: 'Подтверждён',
  rejected: 'Отклонён',
  partially_paid: 'Частично оплачен',
  paid: 'Оплачен',
  canceled: 'Отменён',
}

export function invoiceStatusLabel(status) {
  return INVOICE_STATUS_LABELS[status] || status
}

const PAYOUT_STATUS_LABELS = {
  requested: 'Запрошена',
  processing: 'В обработке',
  succeeded: 'Выполнена',
  failed: 'Ошибка',
  canceled: 'Отменена',
}

export function payoutStatusLabel(status) {
  return PAYOUT_STATUS_LABELS[status] || status
}

export function formatRefundOutcome(decision) {
  if (!decision) return '—'
  if (decision.status === 'pending') {
    return `Ожидает решения до ${formatDateTime(decision.deadline)}`
  }
  if (decision.choice === 'keep') {
    if (decision.status === 'expired') {
      return 'Оставлено семье (срок истёк)'
    }
    return 'Оставлено семье получателя'
  }
  if (decision.choice === 'hold') {
    return 'Оставлено на текущей карточке до завершения проверки'
  }
  if (decision.choice === 'refund') {
    return 'Возврат на баланс (архивная операция)'
  }
  if (decision.choice === 'redirect' && decision.target_card) {
    return `Перенаправлено на «${decision.target_card.full_name}»`
  }
  return decision.choice_label || '—'
}

export function formatBalanceTransactionAmount(transaction) {
  const prefix = transaction.transaction_type === 'refund_in' ? '+' : '−'
  return `${prefix}${formatMoney(transaction.amount)}`
}
