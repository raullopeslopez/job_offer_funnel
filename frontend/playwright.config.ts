import { availableParallelism } from "node:os";
import { defineConfig } from "@playwright/test";
import { defineBddConfig } from "playwright-bdd";
import { apiPort, apiUrl, E2E_TOKEN, webPort, webUrl } from "./e2e/support/env";

// The API's days are the user's (TIMEZONE in backend/src/funnel/core/config.py): the steps
// (Node) and the browser count "today" in the same zone, or near midnight UTC they disagree.
const TIME_ZONE = "Europe/Madrid";
process.env.TZ = TIME_ZONE;

// E2E against the real API with its own throwaway database (backend/tests/support/e2e_server.py).
const testDir = defineBddConfig({
  features: "../specs/ui/*.feature",
  featuresRoot: "../specs/ui",
  steps: ["e2e/**/*.steps.ts", "e2e/support/fixtures.ts"],
  // The public feeds cannot be reached from the E2E API: component tests cover them.
  tags: "not @component",
});

// Each worker brings up its own API, Postgres and Vite, so it takes more than one CPU.
// E2E_WORKERS overrides the default (CI sets it in .github/workflows/frontend.yml).
const WORKERS = Number(
  process.env.E2E_WORKERS ?? Math.min(4, Math.max(1, Math.floor(availableParallelism() / 2))),
);
const workers = [...Array(WORKERS).keys()];

export default defineConfig({
  testDir,
  workers: WORKERS,
  fullyParallel: true, // the scenarios of one feature can go to different workers
  forbidOnly: Boolean(process.env.CI),
  // One retry in CI: a slow runner can miss the 5 s waits once (run 43477597086). A scenario
  // that passes only on its retry is reported as flaky, and its trace is uploaded.
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  // Short waits: a missing element fails in seconds, not after the 30 s test timeout.
  expect: { timeout: 5_000 },
  use: {
    // baseURL is the worker's own Vite: see e2e/support/fixtures.ts.
    timezoneId: TIME_ZONE,
    actionTimeout: 5_000,
    trace: "retain-on-failure",
  },
  // Per worker, one API (with its own database) and one Vite proxying to it.
  webServer: [
    ...workers.map((worker) => ({
      command: "uv run python -m support.e2e_server",
      cwd: "../backend/tests",
      url: `${apiUrl(worker)}/health`,
      env: { E2E_API_PORT: String(apiPort(worker)), E2E_TOKEN },
      timeout: 180_000,
    })),
    ...workers.map((worker) => ({
      command: `pnpm exec vite --host 127.0.0.1 --port ${webPort(worker)} --strictPort`,
      url: webUrl(worker),
      env: { API_URL: apiUrl(worker) },
    })),
  ],
});
