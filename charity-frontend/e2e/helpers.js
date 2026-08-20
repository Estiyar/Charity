import { Buffer } from 'node:buffer'
import crypto from 'node:crypto'
import process from 'node:process'
import { expect } from '@playwright/test'

export const gatewayOrigin = process.env.E2E_GATEWAY_ORIGIN || 'http://127.0.0.1:18080'
export const gatewayApiUrl = process.env.E2E_API_URL || `${gatewayOrigin}/api`

export function uniqueEmail(prefix) {
  return `${prefix}-${Date.now()}-${crypto.randomBytes(3).toString('hex')}@example.test`
}

export function buildPdfUpload(name, body) {
  return {
    name,
    mimeType: 'application/pdf',
    buffer: Buffer.from(`%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n${body}\n%%EOF`, 'utf-8'),
  }
}

export function nextDate(daysAhead) {
  const value = new Date()
  value.setDate(value.getDate() + daysAhead)
  return value.toISOString().slice(0, 10)
}

export async function apiLogin(request, email, password) {
  const response = await request.post(`${gatewayApiUrl}/auth/login`, {
    data: { email, password },
  })
  expect(response.ok()).toBeTruthy()
  return response.json()
}

export async function apiGet(request, path, token) {
  const response = await request.get(`${gatewayApiUrl}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  expect(response.ok()).toBeTruthy()
  return response.json()
}

export async function apiPost(request, path, payload, token, extra = {}) {
  const response = await request.post(`${gatewayApiUrl}${path}`, {
    data: payload,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    ...extra,
  })
  expect(response.ok()).toBeTruthy()
  return response.json()
}

export async function apiMultipart(request, path, form, token) {
  const response = await request.post(`${gatewayApiUrl}${path}`, {
    multipart: form,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  expect(response.ok()).toBeTruthy()
  return response.json()
}

export async function uiLogin(page, email, password) {
  await page.goto('/login')
  await page.getByPlaceholder('Email').fill(email)
  await page.getByPlaceholder('Пароль').fill(password)
  await page.getByRole('button', { name: 'Войти' }).click()
}

export async function uiLogout(page) {
  await page.getByRole('button', { name: 'Выйти' }).click()
}

export async function waitForValue(fetcher, predicate, timeout = 30000) {
  const started = Date.now()
  while (Date.now() - started < timeout) {
    const value = await fetcher()
    if (predicate(value)) {
      return value
    }
    await new Promise((resolve) => setTimeout(resolve, 1000))
  }
  throw new Error('Timed out while waiting for expected state.')
}

export function createNetworkTracker(page) {
  const origins = new Set()
  page.on('request', (request) => {
    const url = request.url()
    if (url.startsWith('data:') || url.startsWith('blob:')) {
      return
    }
    origins.add(new URL(url).origin)
  })
  return origins
}

export function expectGatewayOnlyTraffic(origins, frontendOrigin) {
  const values = Array.from(origins)
  const forbidden = values.filter((origin) => ![frontendOrigin, gatewayOrigin].includes(origin))
  expect(forbidden, `Unexpected browser origins: ${values.join(', ')}`).toEqual([])
}

export async function openAuthorCard(page, cardId) {
  await page.goto(`/author/cards/${cardId}`)
  await expect(page).toHaveURL(new RegExp(`/author/cards/${cardId}$`))
}

export async function openPublicCard(page, cardId) {
  await page.goto(`/cards/${cardId}`)
  await expect(page).toHaveURL(new RegExp(`/cards/${cardId}$`))
}
