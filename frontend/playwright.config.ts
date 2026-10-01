import { defineConfig } from '@playwright/test'
const preview = process.env.DASHBOARD_PREVIEW === '1'
const baseURL = `http://127.0.0.1:${preview ? 4173 : 5173}`
export default defineConfig({
  testDir: './e2e',
  timeout: 60000,
  workers: 1,
  use: {
    baseURL,
    channel: process.platform === 'win32' ? 'msedge' : undefined,
    viewport: { width: 1440, height: 1000 },
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  webServer: {
    command: preview ? 'npm run preview' : 'npm run dev',
    url: baseURL,
    reuseExistingServer: true,
    timeout: 60000,
  },
})
