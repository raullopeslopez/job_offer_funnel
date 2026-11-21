import { test as base, createBdd } from "playwright-bdd";
import { Api } from "./api";
import { apiUrl, webUrl } from "./env";

// Each worker talks to its own Vite and API (playwright.config.ts starts one per worker).
// `api` empties the database before each scenario, so every scenario starts clean.
export const test = base.extend<{ api: Api }>({
  // biome-ignore lint/correctness/noEmptyPattern: Playwright needs the destructuring.
  baseURL: async ({}, use, testInfo) => {
    await use(webUrl(testInfo.parallelIndex));
  },
  api: async ({ request }, use, testInfo) => {
    const api = new Api(request, apiUrl(testInfo.parallelIndex));
    await api.reset();
    await use(api);
  },
});

export const { Given, When, Then } = createBdd(test);
