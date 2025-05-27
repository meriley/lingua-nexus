// Playwright configuration for integration tests
const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests/integration',
  timeout: 30000,
  expect: {
    timeout: 5000
  },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    actionTimeout: 0,
    trace: 'on-first-retry',
    // baseURL: 'https://web.telegram.org/k/',
  },
  webServer: {
    command: 'npx http-server -p 3333 ./mockup',
    port: 3333,
    reuseExistingServer: !process.env.CI,
  },
});