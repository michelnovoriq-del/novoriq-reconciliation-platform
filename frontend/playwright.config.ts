import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 120_000,
  expect: { timeout: 30_000 },
  reporter: "list",
  use: {
    baseURL: process.env.BASE_URL ?? "http://127.0.0.1:3000",
    navigationTimeout: 60_000,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 5"] } },
  ],
  webServer: {
    command: "NEXT_PUBLIC_SITE_URL=http://127.0.0.1:3000 npm run dev",
    url: "http://127.0.0.1:3000",
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
