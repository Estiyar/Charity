import { authHeaders, clearToken, setToken } from './auth'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
export const MEDIA_BASE = import.meta.env.VITE_MEDIA_URL || 'http://localhost:8000'

export function mediaUrl(path) {
  if (!path) return null
  if (path.startsWith('http')) return path
  return `${MEDIA_BASE}${path}`
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
  const fields = ['email', 'password', 'repeat_password', 'role', 'full_name', 'phone', 'iin', 'recipient_iin']
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

export function fetchMedicalRecord(iin) {
  return request(`/medregistry/${iin}/`)
}

export function fetchFraudProfile(iin) {
  return request(`/antifraud/${iin}/`)
}

export function fetchStats() {
  return request('/stats/')
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

export function uploadDocument(cardId, formData) {
  return request(`/cards/${cardId}/documents/`, {
    method: 'POST',
    body: formData,
  })
}

export function fetchCard(id) {
  return request(`/cards/${id}/`)
}

export function fetchDonations(cardId) {
  return request(`/cards/${cardId}/donations/`)
}

export function fetchMyDonations() {
  return request('/donations/my/')
}

export function fetchMyPendingRefunds() {
  return request('/refunds/my/')
}

export function fetchMyRefundHistory() {
  return request('/refunds/history/')
}

export function chooseRefundDecision(decisionId, payload) {
  return request(`/refunds/${decisionId}/choose/`, {
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

export function requestCardRevision(id, comment) {
  return request(`/moderation/cards/${id}/request-revision/`, {
    method: 'POST',
    body: JSON.stringify({ comment }),
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

export function fetchExpenses(cardId) {
  return request(`/cards/${cardId}/expenses/`)
}

export function createExpense(cardId, formData) {
  return request(`/cards/${cardId}/expenses/`, {
    method: 'POST',
    body: formData,
  })
}

export function fetchModerationExpenses() {
  return request('/moderation/expenses/')
}

export function approveExpense(id, comment = '') {
  return request(`/expenses/${id}/approve/`, {
    method: 'POST',
    body: JSON.stringify({ comment }),
  })
}

export function rejectExpense(id, comment) {
  return request(`/expenses/${id}/reject/`, {
    method: 'POST',
    body: JSON.stringify({ comment }),
  })
}

export function requestExpenseClarification(id, comment) {
  return request(`/expenses/${id}/request-clarification/`, {
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
