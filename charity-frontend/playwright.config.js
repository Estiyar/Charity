import { defineConfig, devices } from '@playwright/test'
import process from 'node:process'

const frontendPort = process.env.E2E_FRONTEND_PORT || '4173'
const apiBaseUrl = process.env.E2E_API_URL || 'http://127.0.0.1:18080/api'
const mediaBaseUrl = process.env.E2E_MEDIA_URL || 'http://127.0.0.1:18080'

export default defineConfig({
  testDir: './e2e',
  timeout: 120000,
  expect: {
    timeout: 15000,
  },
  fullyParallel: false,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 4173',
    cwd: '.',
    reuseExistingServer: true,
    timeout: 120000,
    url: `http://127.0.0.1:${frontendPort}`,
    env: {
      VITE_API_URL: apiBaseUrl,
      VITE_MEDIA_URL: mediaBaseUrl,
      VITE_ECP_ALLOW_DEV: 'true',
    },
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
      },
    },
  ],
})
