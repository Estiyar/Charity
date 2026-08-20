import crypto from 'node:crypto'
import { expect, test } from '@playwright/test'
import {
  apiGet,
  apiLogin,
  apiPost,
  buildPdfUpload,
  createNetworkTracker,
  expectGatewayOnlyTraffic,
  gatewayApiUrl,
  nextDate,
  openAuthorCard,
  openPublicCard,
  uiLogin,
  uiLogout,
  uniqueEmail,
  waitForValue,
} from './helpers'

const state = {}
const seededPassword = 'demo123456'

function unreadCountFromText(text) {
  const match = text.match(/Непрочитанных:\s*(\d+)/)
  return match ? Number(match[1]) : 0
}

function lastId(items) {
  return items.reduce((max, item) => Math.max(max, Number(item.id || 0)), 0)
}

async function loginAuthorTokens(request) {
  const auth = await apiLogin(request, state.authorEmail, state.authorPassword)
  state.authorAccess = auth.access
  return auth.access
}

test.describe.serial('e-Komek browser flows', () => {
  test('auth, profile access, role permissions, gateway-only frontend traffic', async ({ page, request, baseURL }) => {
    const health = await request.get('http://127.0.0.1:8080/health')
    expect(health.ok()).toBeTruthy()

    state.authorEmail = uniqueEmail('author-e2e')
    state.authorPassword = 'StrongPass123!'

    const origins = createNetworkTracker(page)

    await page.goto('/register?role=author')
    await page.getByRole('button', { name: 'Локальный тестовый сертификат' }).click()
    await expect(page.getByText('ИВАНОВ ИВАН ИВАНОВИЧ')).toBeVisible()
    await page.getByPlaceholder('Email').fill(state.authorEmail)
    await page.getByPlaceholder('Телефон').fill('+77001112233')
    await page.getByPlaceholder('Пароль').fill(state.authorPassword)
    await page.getByPlaceholder('Повторите пароль').fill(state.authorPassword)
    await page.getByText('Согласен(на) на обработку персональных данных').click()
    await page.getByRole('button', { name: 'Зарегистрироваться' }).click()
    await expect(page).toHaveURL(/\/author$/)

    await page.goto('/profile')
    await expect(page.getByRole('heading', { name: 'Мой профиль' })).toBeVisible()
    await expect(page.getByText('ИВАНОВ ИВАН ИВАНОВИЧ')).toBeVisible()
    await expect(page.getByText('ЭЦП')).toBeVisible()

    await uiLogout(page)
    await expect(page).toHaveURL(/\/login$/)

    await uiLogin(page, state.authorEmail, state.authorPassword)
    await expect(page).toHaveURL(/\/author$/)
    await uiLogout(page)

    await uiLogin(page, 'donor1@charity.test', seededPassword)
    await expect(page).toHaveURL(/\/$/)
    await page.goto('/author/create')
    await expect(page.getByRole('heading', { name: 'Нет доступа' })).toBeVisible()
    await expect(page.getByText('Эта страница доступна только для автора.')).toBeVisible()
    await uiLogout(page)

    expectGatewayOnlyTraffic(origins, new URL(baseURL).origin)
    await loginAuthorTokens(request)
  })

  test('child beneficiary and representation moderation flow', async ({ page, request }) => {
    await uiLogin(page, state.authorEmail, state.authorPassword)
    await page.goto('/author/create')
    await page.getByLabel('Для кого сбор').selectOption('child')
    await page.getByLabel('Тип представительства').selectOption('parent')
    await page.getByLabel('ИИН получателя').fill('010203301122')
    await page.getByRole('button', { name: 'Найти' }).click()
    await expect(page.getByText('Арман Жумабеков')).toBeVisible()
    await expect(page.getByText('Получатель подтверждён.')).toBeVisible()

    await page.goto('/author/beneficiaries')
    await expect(page.getByText('Арман Жумабеков')).toBeVisible()
    await expect(page.getByText('Родитель')).toBeVisible()
    await uiLogout(page)

    const moderatorAuth = await apiLogin(request, 'moderator1@charity.test', seededPassword)
    state.moderatorAccess = moderatorAuth.access

    await uiLogin(page, 'moderator1@charity.test', seededPassword)
    await page.goto('/moderator/representations')
    const childRow = page.locator('article').filter({ hasText: 'Арман Жумабеков' }).first()
    await expect(childRow).toBeVisible()
    await childRow.getByRole('button', { name: 'Подтвердить' }).click()
    await expect(childRow).not.toBeVisible()
    await uiLogout(page)
  })

  test('self fundraiser can be created, moderated, activated, and opened publicly', async ({ page, request }) => {
    const existingCards = await apiGet(request, '/cards/my/', state.authorAccess)
    const beforeId = lastId(existingCards)

    await uiLogin(page, state.authorEmail, state.authorPassword)
    await page.goto('/author/create')
    await page.getByRole('button', { name: 'Подтвердить получателя по ЭЦП автора' }).click()
    await expect(page.getByText('Получатель подтверждён.')).toBeVisible()
    await page.getByLabel('Описание').fill(`Self fundraiser ${Date.now()}`)
    await page.getByLabel('Целевая сумма').fill('150000')
    await page.getByLabel('Дата окончания сбора').fill(nextDate(30))
    await page.getByLabel('Номер удостоверения').fill('SELF-001')
    await page.getByLabel('Телефон для связи').fill('+77001112233')
    await page.getByLabel('Email для связи').fill(state.authorEmail)
    await page.getByLabel('Клиника или организация').fill('Семейная поликлиника №12')
    await page.getByLabel('Дата выдачи документа').fill(nextDate(-10))
    await page.getByLabel('Срок действия документа').fill(nextDate(180))
    await page.getByLabel('Выбрать файлы').setInputFiles([
      buildPdfUpload('self-medical.pdf', 'self medical document'),
    ])
    await page.getByText('Согласен(на) на обработку персональных данных').click()
    await page.getByRole('button', { name: 'Отправить на модерацию' }).click()
    await expect(page).toHaveURL(/\/author$/)
    await uiLogout(page)

    const selfCard = await waitForValue(
      () => apiGet(request, '/cards/my/', state.authorAccess),
      (items) => lastId(items) > beforeId,
    )
    state.selfCardId = lastId(selfCard)

    await uiLogin(page, 'moderator1@charity.test', seededPassword)
    await page.goto(`/moderator/cards/${state.selfCardId}`)
    await expect(page.getByRole('heading', { name: 'ИВАНОВ ИВАН ИВАНОВИЧ' })).toBeVisible()
    await page.getByRole('button', { name: 'Проверен' }).first().click()
    await page.getByRole('button', { name: 'Одобрить' }).click()
    await expect(page.getByText('Действие выполнено успешно')).toBeVisible()
    await uiLogout(page)

    await waitForValue(
      () => apiGet(request, `/cards/${state.selfCardId}/`, null),
      (card) => card.status === 'active',
    )

    await openPublicCard(page, state.selfCardId)
    await expect(page.getByRole('heading', { name: 'ИВАНОВ ИВАН ИВАНОВИЧ' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Сделать пожертвование' })).toBeVisible()
  })

  test('other-person fundraiser supports revision and resubmission', async ({ page, request }) => {
    const beforeCards = await apiGet(request, '/cards/my/', state.authorAccess)
    const beforeId = lastId(beforeCards)

    await uiLogin(page, state.authorEmail, state.authorPassword)
    await page.goto('/author/create')
    await page.getByLabel('Сохранённый получатель').selectOption('')
    await page.getByLabel('Для кого сбор').selectOption('other')
    await page.getByLabel('ИИН получателя').fill('960101300567')
    await page.getByRole('button', { name: 'Найти' }).click()
    await expect(page.getByText('Ерлан Нурланов')).toBeVisible()
    await page.getByLabel('Описание').fill(`Revision fundraiser ${Date.now()}`)
    await page.getByLabel('Целевая сумма').fill('99000')
    await page.getByLabel('Дата окончания сбора').fill(nextDate(45))
    await page.getByLabel('Номер удостоверения').fill('OTHER-001')
    await page.getByLabel('Телефон для связи').fill('+77002223344')
    await page.getByLabel('Email для связи').fill(state.authorEmail)
    await page.getByLabel('Клиника или организация').fill('Онкологический центр')
    await page.getByLabel('Дата выдачи документа').fill(nextDate(-15))
    await page.getByLabel('Срок действия документа').fill(nextDate(120))
    await page.getByLabel('Выбрать файлы').setInputFiles([
      buildPdfUpload('other-medical.pdf', 'other medical document'),
    ])
    await page.getByText('Согласен(на) на обработку персональных данных').click()
    await page.getByRole('button', { name: 'Отправить на модерацию' }).click()
    await expect(page).toHaveURL(/\/author$/)
    await uiLogout(page)

    const createdCards = await waitForValue(
      () => apiGet(request, '/cards/my/', state.authorAccess),
      (items) => lastId(items) > beforeId,
    )
    state.revisionCardId = lastId(createdCards)

    await uiLogin(page, 'moderator1@charity.test', seededPassword)
    await page.goto('/moderator/representations')
    const otherRepresentation = page.locator('article').filter({ hasText: 'Ерлан Нурланов' }).first()
    await expect(otherRepresentation).toBeVisible()
    await otherRepresentation.getByRole('button', { name: 'Подтвердить' }).click()

    await page.goto(`/moderator/cards/${state.revisionCardId}`)
    await page.getByRole('button', { name: 'Проверен' }).first().click()
    await page.locator('textarea').first().fill('Нужно уточнить диагноз и клинику.')
    await page.getByRole('button', { name: 'На доработку' }).click()
    await expect(page.getByText('Действие выполнено успешно')).toBeVisible()
    await uiLogout(page)

    await uiLogin(page, state.authorEmail, state.authorPassword)
    await openAuthorCard(page, state.revisionCardId)
    await expect(page.getByText('Нужно уточнить диагноз и клинику.')).toBeVisible()
    await page.getByRole('textbox').first().fill('Исправленное описание для повторной проверки.')
    await page.getByPlaceholder('Диагноз').fill('Онкология')
    await page.getByPlaceholder('Клиника').fill('Онкологический центр Алматы')
    await page.getByRole('button', { name: 'Сохранить и отправить снова' }).click()
    await uiLogout(page)

    await waitForValue(
      () => apiGet(request, `/cards/${state.revisionCardId}/`, state.authorAccess),
      (card) => card.status !== 'revision_required',
    )

    await uiLogin(page, 'moderator1@charity.test', seededPassword)
    await page.goto(`/moderator/cards/${state.revisionCardId}`)
    await page.getByRole('button', { name: 'Одобрить' }).click()
    await expect(page.getByText('Действие выполнено успешно')).toBeVisible()
    await uiLogout(page)

    await waitForValue(
      () => apiGet(request, `/cards/${state.revisionCardId}/`, null),
      (card) => card.status === 'active',
    )
  })

  test('donation succeeds once, duplicate completion is idempotent, and notifications work', async ({ page, request }) => {
    const beforeCard = await apiGet(request, `/cards/${state.selfCardId}/`, null)
    const beforeCollected = beforeCard.collected_amount

    await openPublicCard(page, state.selfCardId)
    await page.getByRole('button', { name: '5 000 ₸' }).click().catch(async () => {
      await page.getByRole('button', { name: /5.*000/ }).click()
    })
    await page.getByPlaceholder('Ваше имя').fill('Playwright Donor')
    await page.getByPlaceholder('Email').fill(uniqueEmail('donor'))
    await page.getByText('Согласен(на) на обработку персональных данных').click()
    await page.getByRole('button', { name: 'Перейти к оплате' }).click()
    await expect(page).toHaveURL(/\/payments\/dev-checkout\/\d+$/)

    const paymentId = Number(page.url().match(/\/payments\/dev-checkout\/(\d+)$/)?.[1])
    state.paymentId = paymentId

    await page.getByRole('button', { name: 'Оплатить успешно' }).click()
    await expect(page).toHaveURL(new RegExp(`/payments/result\\?payment=${paymentId}$`))

    const successCard = await waitForValue(
      () => apiGet(request, `/cards/${state.selfCardId}/`, null),
      (card) => card.collected_amount !== beforeCollected,
    )
    expect(successCard.collected_amount).toBe('5000.00')

    await apiPost(request, `/payments/dev/${paymentId}/complete`, { outcome: 'success' }, null)
    const duplicatedCard = await apiGet(request, `/cards/${state.selfCardId}/`, null)
    expect(duplicatedCard.collected_amount).toBe('5000.00')

    await uiLogin(page, state.authorEmail, state.authorPassword)
    await page.goto('/notifications')
    const summaryBefore = await page.locator('section').first().textContent()
    const unreadBefore = unreadCountFromText(summaryBefore || '')
    expect(unreadBefore).toBeGreaterThan(0)
    await page.getByRole('button', { name: 'Отметить прочитанным' }).first().click()
    await expect(page.getByRole('button', { name: 'Пометить непрочитанным' }).first()).toBeVisible()
    const summaryAfterRead = await page.locator('section').first().textContent()
    expect(unreadCountFromText(summaryAfterRead || '')).toBeLessThan(unreadBefore)
    await page.getByRole('button', { name: 'Пометить непрочитанным' }).first().click()
    const summaryAfterUnread = await page.locator('section').first().textContent()
    expect(unreadCountFromText(summaryAfterUnread || '')).toBeGreaterThanOrEqual(unreadBefore)
    await page.getByRole('link', { name: 'Перейти' }).first().click()
    await expect(page).toHaveURL(/\/author\/cards\/\d+$/)
    await uiLogout(page)
  })

  test('expense approval updates public reporting safely', async ({ page, request }) => {
    await uiLogin(page, state.authorEmail, state.authorPassword)
    await openAuthorCard(page, state.selfCardId)
    await page.getByRole('heading', { name: 'Добавить расход' }).scrollIntoViewIfNeeded()
    await page.locator('input[type="date"]').first().fill(nextDate(-1))
    await page.getByPlaceholder('Назначение').fill('Оплата лекарства')
    await page.getByPlaceholder('Сумма').fill('2500')
    await page.getByPlaceholder('Комментарий').fill('Проверочный расход')
    await page.getByLabel('Выбрать файл').nth(1).setInputFiles(buildPdfUpload('expense.pdf', 'expense document'))
    await page.getByRole('button', { name: 'Отправить на проверку' }).click()
    await expect(page.getByText('Расход отправлен на проверку модератору.')).toBeVisible()
    await uiLogout(page)

    const authorExpenses = await waitForValue(
      () => apiGet(request, `/cards/${state.selfCardId}/expenses/`, state.authorAccess),
      (items) => items.some((item) => item.purpose === 'Оплата лекарства'),
    )
    state.expenseId = authorExpenses.find((item) => item.purpose === 'Оплата лекарства').id

    await uiLogin(page, 'moderator1@charity.test', seededPassword)
    await page.goto(`/moderator/expenses/${state.expenseId}`)
    await page.getByRole('button', { name: 'Одобрить' }).click()
    await expect(page).toHaveURL(/\/moderator\/expenses$/)
    await uiLogout(page)

    await waitForValue(
      () => apiGet(request, `/cards/${state.selfCardId}/expenses/public/`, null),
      (report) => (report.expenses || []).some((item) => item.purpose === 'Оплата лекарства'),
    )

    await openPublicCard(page, state.selfCardId)
    await expect(page.getByText('Оплата лекарства')).toBeVisible()
    await expect(page.getByText('2 500 ₸').first()).toBeVisible().catch(async () => {
      await expect(page.getByText(/2.*500/).first()).toBeVisible()
    })
    const expenseReportText = await page.textContent('body')
    expect(expenseReportText).not.toContain('Проверочный расход')
  })

  test('clinic payout uses signed callback and remains idempotent', async ({ page, request }) => {
    await uiLogin(page, state.authorEmail, state.authorPassword)
    await openAuthorCard(page, state.selfCardId)
    await page.getByRole('heading', { name: 'Прямая оплата клинике' }).scrollIntoViewIfNeeded()
    await page.locator('form').filter({ hasText: 'Прямая оплата клинике' }).locator('input[type="date"]').fill(nextDate(-1))
    await page.getByPlaceholder('Название организации').fill('Клиника Астана')
    await page.getByPlaceholder('БИН').fill('123456789012')
    await page.getByPlaceholder('IBAN').fill('KZ86125KZT5004100100')
    await page.getByPlaceholder('Банк').fill('Halyk Bank')
    await page.getByPlaceholder('Номер счёта').fill('INV-001')
    await page.locator('form').filter({ hasText: 'Прямая оплата клинике' }).getByPlaceholder('Сумма').fill('1500')
    await page.locator('form').filter({ hasText: 'Прямая оплата клинике' }).getByPlaceholder('Комментарий').fill('Тестовый счёт клиники')
    await page.getByLabel('Счёт PDF, JPG или PNG').setInputFiles(buildPdfUpload('invoice.pdf', 'invoice document'))
    await page.getByRole('button', { name: 'Отправить счёт на проверку' }).click()
    await expect(page.getByText('Счёт отправлен на проверку.')).toBeVisible()
    await uiLogout(page)

    const invoices = await waitForValue(
      () => apiGet(request, `/cards/${state.selfCardId}/invoices/`, state.authorAccess),
      (items) => items.some((item) => item.organization?.name === 'Клиника Астана'),
    )
    state.invoiceId = invoices.find((item) => item.organization?.name === 'Клиника Астана').id

    await uiLogin(page, 'moderator1@charity.test', seededPassword)
    await page.goto(`/moderator/invoices/${state.invoiceId}`)
    await page.locator('textarea').fill('Организация и сумма подтверждены.')
    await page.getByRole('button', { name: 'Подтвердить организацию и сумму' }).click()
    await expect(page).toHaveURL(/\/moderator\/invoices$/)
    await uiLogout(page)

    const invoiceDetails = await waitForValue(
      () => apiGet(request, `/invoices/${state.invoiceId}/`, state.moderatorAccess),
      (invoice) => Array.isArray(invoice.payouts) && invoice.payouts.length > 0,
    )
    const payoutId = invoiceDetails.payouts[0].id
    const payout = await apiGet(request, `/payouts/${payoutId}/`, state.moderatorAccess)

    const payload = {
      payout_id: String(payout.id),
      provider_payout_id: payout.provider_payout_id,
      amount: String(payout.amount),
      currency: payout.currency,
      card_id: payout.card_id,
      status: 'succeeded',
    }
    const body = JSON.stringify(payload)
    const signature = crypto.createHmac('sha256', 'dev-payout-secret').update(body).digest('hex')

    const first = await request.post(`${gatewayApiUrl}/payouts/webhook/dev`, {
      data: payload,
      headers: {
        'X-Dev-Signature': signature,
      },
    })
    expect(first.ok()).toBeTruthy()

    const second = await request.post(`${gatewayApiUrl}/payouts/webhook/dev`, {
      data: payload,
      headers: {
        'X-Dev-Signature': signature,
      },
    })
    expect(second.ok()).toBeTruthy()

    const report = await waitForValue(
      () => apiGet(request, `/cards/${state.selfCardId}/expenses/public/`, null),
      (value) => Number(value.total_direct_payouts || 0) >= 1500,
    )

    expect(report.total_direct_payouts).toBe('1500.00')

    await openPublicCard(page, state.selfCardId)
    const bodyText = await page.textContent('body')
    expect(bodyText).toContain('Клиника Астана')
    expect(bodyText).not.toContain('KZ86125KZT5004100100')
    expect(bodyText).not.toContain('123456789012')
  })

  test('public report suspends card, donations are blocked, and card can be unsuspended after resolution', async ({ page, request }) => {
    await openPublicCard(page, state.selfCardId)
    await page.getByRole('combobox').last().selectOption('suspected_fraud')
    await page.getByPlaceholder('Опишите проблему подробно').fill('Есть признаки мошенничества, проверьте сбор повторно.')
    await page.getByRole('button', { name: 'Отправить жалобу' }).click()
    await expect(page.getByText('Жалоба отправлена в очередь модерации.')).toBeVisible()

    const suspendedCard = await waitForValue(
      () => apiGet(request, `/cards/${state.selfCardId}/`, null),
      (card) => card.status === 'suspended',
    )
    expect(suspendedCard.status).toBe('suspended')

    await page.reload()
    await expect(page.getByText('Сбор временно приостановлен.')).toBeVisible()
    await expect(page.getByText('Новые пожертвования временно недоступны.')).toBeVisible()

    await uiLogin(page, 'moderator1@charity.test', seededPassword)
    await page.goto('/moderator/reports')
    const reportRow = page.locator('article').filter({ hasText: `Сбор #${state.selfCardId}` }).first()
    await expect(reportRow).toBeVisible()
    await reportRow.locator('textarea').fill('Проверка проведена, жалоба обработана.')
    await reportRow.getByRole('button', { name: 'Подтвердить' }).click()
    await uiLogout(page)

    await apiPost(request, `/cards/${state.selfCardId}/unsuspend/`, { reason: 'Жалоба обработана' }, state.moderatorAccess)
    await waitForValue(
      () => apiGet(request, `/cards/${state.selfCardId}/`, null),
      (card) => card.status === 'active',
    )

    await openPublicCard(page, state.selfCardId)
    await expect(page.getByRole('heading', { name: 'Сделать пожертвование' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Перейти к оплате' })).toBeVisible()
  })
})
