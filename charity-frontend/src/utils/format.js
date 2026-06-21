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
  if (decision.choice === 'refund') {
    const netAmount = decision.refund_payout?.net_amount
    return netAmount ? `Возврат на баланс ${formatMoney(netAmount)}` : 'Возврат на баланс'
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
