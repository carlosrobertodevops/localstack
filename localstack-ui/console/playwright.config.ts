import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "tests/e2e",
  retries: 1,
  timeout: 30_000,
  fullyParallel: true,
  use: {
    baseURL: process.env.CONSOLE_URL ?? "http://localhost:4577",
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
