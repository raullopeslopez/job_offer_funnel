import { test as base, createBdd } from "playwright-bdd";
import { Api } from "./api";

// `api` empties the database before each scenario, so every scenario starts clean.
export const test = base.extend<{ api: Api }>({
  api: async ({ request }, use) => {
    const api = new Api(request);
    await api.reset();
    await use(api);
  },
});

export const { Given, When, Then } = createBdd(test);
