import { defineConfig } from "@playwright/test";
import { defineBddConfig } from "playwright-bdd";
import { API_PORT, API_URL, E2E_TOKEN, WEB_PORT } from "./e2e/support/env";

// E2E against the real API with its own throwaway database (backend/tests/support/e2e_server.py).
const testDir = defineBddConfig({
  features: "../specs/ui/*.feature",
  featuresRoot: "../specs/ui",
  steps: ["e2e/**/*.steps.ts", "e2e/support/fixtures.ts"],
  // The public feeds cannot be reached from the E2E API: component tests cover them.
  tags: "not @component",
});

export default defineConfig({
  testDir,
  workers: 1, // one database for every scenario
  forbidOnly: Boolean(process.env.CI),
  // One retry in CI: a slow runner can miss the 5 s waits once (run 43477597086). A scenario
  // that passes only on its retry is reported as flaky, and its trace is uploaded.
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  // Short waits: a missing element fails in seconds, not after the 30 s test timeout.
  expect: { timeout: 5_000 },
  use: {
    baseURL: `http://127.0.0.1:${WEB_PORT}`,
    actionTimeout: 5_000,
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: "uv run python -m support.e2e_server",
      cwd: "../backend/tests",
      url: `${API_URL}/health`,
      env: { E2E_API_PORT: String(API_PORT), E2E_TOKEN },
      timeout: 180_000,
    },
    {
      command: `pnpm exec vite --host 127.0.0.1 --port ${WEB_PORT} --strictPort`,
      url: `http://127.0.0.1:${WEB_PORT}`,
      env: { API_URL },
    },
  ],
});
