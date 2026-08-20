import { authHeaders, clearToken, getToken, setToken } from './auth'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8080/api'
export const MEDIA_BASE = import.meta.env.VITE_MEDIA_URL || 'http://localhost:8080'

export function mediaUrl(path) {
  if (!path) return null
  if (path.startsWith('http')) return path
  return `${MEDIA_BASE}${path}`
}

export function parseApiFieldErrors(data) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) return {}
  const fields = {}
  for (const [key, value] of Object.entries(data)) {
    if (key === 'detail') continue
    if (key === 'non_field_errors') {
      if (Array.isArray(value) && value[0]) fields._form = value[0]
      continue
    }
    if (Array.isArray(value) && value[0]) fields[key] = value[0]
    else if (typeof value === 'string' && value) fields[key] = value
  }
  return fields
}

export function parseApiError(data, fallback = 'Запрос не выполнен.') {
  if (!data) return fallback
  if (typeof data === 'string') return data
  if (Array.isArray(data) && data[0]) return data[0]
  if (typeof data !== 'object') return fallback
  if (typeof data.detail === 'string') return data.detail
  if (Array.isArray(data.detail) && data.detail[0]) return data.detail[0]
  if (Array.isArray(data.non_field_errors) && data.non_field_errors[0]) {
    return data.non_field_errors[0]
  }
  for (const value of Object.values(data)) {
    if (Array.isArray(value) && value[0]) return value[0]
    if (typeof value === 'string' && value) return value
  }
  const fields = ['email', 'password', 'repeat_password', 'role', 'full_name', 'phone', 'city', 'bio', 'public_fields', 'birth_date', 'iin', 'recipient_iin', 'personal_data_consent', 'ecp_session_token']
  for (const field of fields) {
    if (Array.isArray(data[field]) && data[field][0]) return data[field][0]
  }
  return fallback
}

async function request(path, options = {}) {
  const { authenticated = true, ...fetchOptions } = options
  const isFormData = fetchOptions.body instanceof FormData
  const response = await fetch(`${API_BASE}${path}`, {
    ...fetchOptions,
    headers: {
      ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
      ...(authenticated ? authHeaders() : {}),
      ...fetchOptions.headers,
    },
  })
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const error = new Error(data?.detail || 'Request failed')
    error.status = response.status
    error.data = data
    throw error
  }
  return data
}

export function register(payload) {
  return request('/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
    authenticated: false,
  })
}

export function requestEcpChallenge() {
  return request('/auth/ecp/challenge', {
    method: 'POST',
    body: JSON.stringify({}),
    authenticated: false,
  })
}

export function verifyEcpSignature(payload) {
  return request('/auth/ecp/verify', {
    method: 'POST',
    body: JSON.stringify(payload),
    authenticated: false,
  })
}

export function registerWithEcp(payload) {
  return request('/auth/register/ecp', {
    method: 'POST',
    body: JSON.stringify(payload),
    authenticated: false,
  })
}

export function login(email, password) {
  return request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
    authenticated: false,
  }).then((data) => {
    setToken(data.access)
    return data
  })
}

export function logout() {
  return request('/auth/logout', { method: 'POST' }).finally(clearToken)
}

export function fetchMe() {
  return request('/auth/me')
}

export function fetchNotifications(params = {}) {
  const query = new URLSearchParams(params).toString()
  return request(`/notifications${query ? `?${query}` : ''}`)
}

export function markNotificationRead(notificationId) {
  return request(`/notifications/${notificationId}/read`, { method: 'POST' })
}

export function markNotificationUnread(notificationId) {
  return request(`/notifications/${notificationId}/unread`, { method: 'POST' })
}

export function markAllNotificationsRead() {
  return request('/notifications/read-all', { method: 'POST' })
}

export function fetchMyProfile() {
  return request('/profile/me')
}

export function updateMyProfile(payload) {
  const isFormData = payload instanceof FormData
  return request('/profile/me', {
    method: 'PATCH',
    body: isFormData ? payload : JSON.stringify(payload),
  })
}

export function fetchUserProfile(userId) {
  return request(`/profile/${userId}`, { authenticated: Boolean(getToken()) })
}

export function updateUserProfile(userId, payload) {
  return request(`/profile/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function fetchMyBalance() {
  return request('/auth/balance/')
}

export function withdrawBalance(amount) {
  const body = amount ? JSON.stringify({ amount }) : JSON.stringify({})
  return request('/auth/balance/withdraw/', {
    method: 'POST',
    body,
  })
}

export function verifyCardRecipient(payload) {
  return request('/cards/recipient/verify', {
    method: 'POST',
    body: JSON.stringify(payload),
    authenticated: true,
  })
}

export function fetchBeneficiaries() {
  return request('/beneficiaries')
}

export function fetchBeneficiary(id) {
  return request(`/beneficiaries/${id}`)
}

export function updateBeneficiary(id, payload) {
  return request(`/beneficiaries/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function fetchRepresentations() {
  return request('/representations')
}

export function verifyRepresentation(payload) {
  return request('/representations/verify', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function fetchModerationRepresentations(status = '') {
  const suffix = status ? `?status=${status}` : ''
  return request(`/representations/moderation${suffix}`)
}

export function confirmRepresentation(id) {
  return request(`/representations/${id}/confirm`, { method: 'POST', body: JSON.stringify({}) })
}

export function rejectRepresentation(id, reason) {
  return request(`/representations/${id}/reject`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  })
}

export function fetchMedicalRecord(iin) {
  return request('/medregistry/lookup/', {
    method: 'POST',
    body: JSON.stringify({ iin }),
  })
}

export function fetchFraudProfile(iin) {
  return request('/antifraud/lookup/', {
    method: 'POST',
    body: JSON.stringify({ iin }),
  })
}

export function fetchStats() {
  return request('/stats/')
}

export function fetchCatalog(params = {}) {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, value)
  })
  const suffix = query.toString() ? `?${query}` : ''
  return request(`/catalog/${suffix}`)
}

export function fetchCatalogReferences() {
  return request('/catalog/references/')
}

export function fetchCards(params = {}) {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value) query.set(key, value)
  })
  const suffix = query.toString() ? `?${query}` : ''
  return request(`/cards/${suffix}`)
}

export function fetchMyCards() {
  return request('/cards/my/')
}

export function createCard(formData) {
  return request('/cards/', {
    method: 'POST',
    body: formData,
  })
}

export function submitCard(cardId) {
  return request(`/cards/${cardId}/submit/`, { method: 'POST' })
}

export function updateCard(cardId, payload) {
  return request(`/cards/${cardId}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function uploadDocument(cardId, formData) {
  return request(`/cards/${cardId}/documents/`, {
    method: 'POST',
    body: formData,
  })
}

export function fetchCardDocuments(cardId) {
  return request(`/cards/${cardId}/documents/`)
}

export function fetchPublicCardDocuments(cardId) {
  return request(`/cards/${cardId}/documents/public/`, { authenticated: false })
}

export function fetchDocumentVersions(documentId) {
  return request(`/documents/${documentId}/versions/`)
}

export async function fetchDocumentOriginalBlob(documentId) {
  const response = await fetch(`${API_BASE}/documents/${documentId}/original/`, {
    headers: authHeaders(),
  })
  if (!response.ok) {
    const error = new Error('Request failed')
    error.status = response.status
    throw error
  }
  return URL.createObjectURL(await response.blob())
}

export function fetchCard(id) {
  return request(`/cards/${id}/`)
}

export function fetchCardTrustStatus(id) {
  return request(`/cards/${id}/trust-status/`)
}

export function fetchCardHistory(id) {
  return request(`/cards/${id}/history/`)
}

export function fetchDonations(cardId) {
  return request(`/cards/${cardId}/donations/`)
}

export function fetchMyDonations() {
  return request('/donations/my/')
}

export function fetchMyPendingRedistributions() {
  return request('/redistribution/my/')
}

export function fetchMyRedistributionHistory() {
  return request('/redistribution/history/')
}

export function chooseRedistribution(decisionId, payload) {
  return request(`/redistribution/${decisionId}/choose/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function donate(cardId, payload) {
  return request(`/cards/${cardId}/donate/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function createPaymentSession(payload) {
  return request('/payments/session', {
    method: 'POST',
    body: JSON.stringify(payload),
    authenticated: Boolean(getToken()),
  })
}

export function fetchPayment(paymentId) {
  return request(`/payments/${paymentId}`, { authenticated: Boolean(getToken()) })
}

export function completeDevPayment(paymentId, outcome) {
  return request(`/payments/dev/${paymentId}/complete`, {
    method: 'POST',
    body: JSON.stringify({ outcome }),
    authenticated: Boolean(getToken()),
  })
}

export function fetchModerationCards(status = '') {
  const suffix = status ? `?status=${status}` : ''
  return request(`/moderation/cards/${suffix}`)
}

export function fetchModerationCard(id) {
  return request(`/moderation/cards/${id}/`)
}

export function approveCard(id, comment = '') {
  return request(`/moderation/cards/${id}/approve/`, {
    method: 'POST',
    body: JSON.stringify({ comment }),
  })
}

export function rejectCard(id, comment) {
  return request(`/moderation/cards/${id}/reject/`, {
    method: 'POST',
    body: JSON.stringify({ comment }),
  })
}

export function requestCardRevision(id, revisionComment, internalComment = '') {
  return request(`/moderation/cards/${id}/request-revision/`, {
    method: 'POST',
    body: JSON.stringify({
      comment: revisionComment,
      revision_comment: revisionComment,
      internal_comment: internalComment,
    }),
  })
}

export function fetchManualReviews(params = {}) {
  const query = new URLSearchParams()
  if (params.subject_type) query.set('subject_type', params.subject_type)
  if (params.status) query.set('status', params.status)
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return request(`/moderation/reviews/${suffix}`)
}

export function fetchManualReview(id) {
  return request(`/moderation/reviews/${id}/`)
}

export function decideManualReview(id, action, payload = {}) {
  return request(`/moderation/reviews/${id}/${action}/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function fetchModerationDocuments() {
  return request('/moderation/documents/')
}

export function verifyDocument(id, payload = {}) {
  return request(`/documents/${id}/verify/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function rejectDocument(id, comment) {
  return request(`/documents/${id}/reject/`, {
    method: 'POST',
    body: JSON.stringify({ comment }),
  })
}

export function requestDocumentRevision(id, revisionComment, internalComment = '') {
  return request(`/documents/${id}/request-revision/`, {
    method: 'POST',
    body: JSON.stringify({
      comment: revisionComment,
      revision_comment: revisionComment,
      internal_comment: internalComment,
    }),
  })
}

export function fetchExpenses(cardId) {
  return request(`/cards/${cardId}/expenses/`)
}

export function fetchPublicExpenseReport(cardId) {
  return request(`/cards/${cardId}/expenses/public/`, { authenticated: false })
}

export function createExpense(cardId, formData) {
  return request(`/cards/${cardId}/expenses/`, {
    method: 'POST',
    body: formData,
  })
}

export function submitExpense(id) {
  return request(`/expenses/${id}/submit/`, { method: 'POST', body: JSON.stringify({}) })
}

export function cancelExpense(id) {
  return request(`/expenses/${id}/cancel/`, { method: 'POST', body: JSON.stringify({}) })
}

export function updateExpense(id, payload) {
  return request(`/expenses/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export async function fetchExpenseOriginalBlob(expenseId) {
  const response = await fetch(`${API_BASE}/expenses/${expenseId}/original/`, {
    headers: authHeaders(),
  })
  if (!response.ok) {
    const error = new Error('Request failed')
    error.status = response.status
    throw error
  }
  return URL.createObjectURL(await response.blob())
}

export function fetchExpense(id) {
  return request(`/expenses/${id}/`)
}

export function fetchModerationExpenses() {
  return request('/moderation/expenses/')
}

export function approveExpense(id, comment = '', publishReceipt) {
  const payload = { comment }
  if (publishReceipt !== undefined) payload.publish_receipt = publishReceipt
  return request(`/expenses/${id}/approve/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function rejectExpense(id, comment) {
  return request(`/expenses/${id}/reject/`, {
    method: 'POST',
    body: JSON.stringify({ comment }),
  })
}

export function requestExpenseClarification(id, revisionComment, internalComment = '') {
  return request(`/expenses/${id}/request-clarification/`, {
    method: 'POST',
    body: JSON.stringify({
      comment: revisionComment,
      revision_comment: revisionComment,
      internal_comment: internalComment,
    }),
  })
}

export function fetchCardInvoices(cardId) {
  return request(`/cards/${cardId}/invoices/`)
}

export function createInvoice(cardId, formData) {
  return request(`/cards/${cardId}/invoices/`, {
    method: 'POST',
    body: formData,
  })
}

export function fetchInvoice(id) {
  return request(`/invoices/${id}/`)
}

export function cancelInvoice(id) {
  return request(`/invoices/${id}/cancel/`, { method: 'POST', body: JSON.stringify({}) })
}

export async function fetchInvoiceOriginalBlob(invoiceId) {
  const response = await fetch(`${API_BASE}/invoices/${invoiceId}/original/`, {
    headers: authHeaders(),
  })
  if (!response.ok) {
    const error = new Error('Request failed')
    error.status = response.status
    throw error
  }
  return URL.createObjectURL(await response.blob())
}

export function fetchModerationInvoices() {
  return request('/moderation/invoices/')
}

export function verifyInvoice(id, comment = '') {
  return request(`/invoices/${id}/verify/`, {
    method: 'POST',
    body: JSON.stringify({ comment }),
  })
}

export function rejectInvoice(id, comment) {
  return request(`/invoices/${id}/reject/`, {
    method: 'POST',
    body: JSON.stringify({ comment }),
  })
}

export function fetchAdminUsers() {
  return request('/admin/users/')
}

export function assignUserRole(userId, role) {
  return request(`/admin/users/${userId}/`, {
    method: 'PATCH',
    body: JSON.stringify({ role }),
  })
}

export function blockUser(userId) {
  return request(`/admin/users/${userId}/`, {
    method: 'PATCH',
    body: JSON.stringify({ status: 'blocked' }),
  })
}

export function unblockUser(userId) {
  return request(`/admin/users/${userId}/`, {
    method: 'PATCH',
    body: JSON.stringify({ status: 'active' }),
  })
}

export function fetchAdminModerators() {
  return request('/admin/moderators/')
}

export function fetchAdminCards() {
  return request('/admin/cards/')
}

export function changeCardStatus(cardId, status) {
  return request(`/admin/cards/${cardId}/set-status/`, {
    method: 'POST',
    body: JSON.stringify({ status }),
  })
}

export function fetchAdminDonations() {
  return request('/admin/donations/')
}

export function fetchAdminExpenses() {
  return request('/admin/expenses/')
}

export function fetchAdminLogs() {
  return request('/admin/moderation-logs/')
}

export function fetchAdminCities() {
  return request('/admin/cities/')
}

export function createCity(name) {
  return request('/admin/cities/', {
    method: 'POST',
    body: JSON.stringify({ name }),
  })
}

export function deleteCity(id) {
  return request(`/admin/cities/${id}/`, { method: 'DELETE' })
}

export function fetchAdminDiagnoses() {
  return request('/admin/diagnoses/')
}

export function createDiagnosis(name) {
  return request('/admin/diagnoses/', {
    method: 'POST',
    body: JSON.stringify({ name }),
  })
}

export function deleteDiagnosis(id) {
  return request(`/admin/diagnoses/${id}/`, { method: 'DELETE' })
}

export function fetchAdminSettings() {
  return request('/admin/settings/')
}

export function updateAdminSettings(payload) {
  return request('/admin/settings/', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function submitCardReport(cardId, { category, description, attachment }) {
  const body = new FormData()
  body.append('category', category)
  body.append('description', description)
  if (attachment) body.append('attachment', attachment)
  return request(`/cards/${cardId}/reports/`, {
    method: 'POST',
    body,
    authenticated: false,
  })
}

export function fetchModerationReports(params = {}) {
  const query = new URLSearchParams(params).toString()
  return request(`/moderation/reports/${query ? `?${query}` : ''}`)
}

export function resolveModerationReport(reportId, payload) {
  return request(`/moderation/reports/${reportId}/resolve/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function suspendCard(cardId, reason) {
  return request(`/cards/${cardId}/suspend/`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  })
}

export function unsuspendCard(cardId, reason) {
  return request(`/cards/${cardId}/unsuspend/`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  })
}

export function fetchAdminRiskConfig() {
  return request('/admin/risk-config/')
}

export function updateAdminRiskConfig(payload) {
  return request('/admin/risk-config/', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function fetchAdminRiskConfigHistory() {
  return request('/admin/risk-config/history/')
}

export function fetchCardRisk(cardId) {
  return request(`/cards/${cardId}/risk/`)
}

export function recalculateCardRisk(cardId) {
  return request(`/cards/${cardId}/risk/recalculate/`, { method: 'POST' })
}

export function overrideCardRisk(cardId, payload) {
  return request(`/cards/${cardId}/risk/override/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
