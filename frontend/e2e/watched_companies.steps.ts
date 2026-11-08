import { expect, type Locator, type Page } from "@playwright/test";
import type { components } from "../src/api/schema";
import { Given, Then, When } from "./support/fixtures";
import { fieldLabel, quoted } from "./support/form";

// The @component scenarios (importing) are covered by WatchedCompaniesPage.test.tsx.

type Ats = components["schemas"]["Ats"];

// See searches.steps.ts: the name cells are found by their column, outside getByRole("grid").
const nameCells = (page: Page) => page.locator('[role="gridcell"][data-field="name"]');
const row = (page: Page, name: string): Locator =>
  page
    .getByRole("grid")
    .getByRole("row")
    .filter({ has: page.getByRole("gridcell", { name, exact: true }) });

async function stopWatching(page: Page, name: string, answer: "Stop watching" | "Cancel") {
  await row(page, name).getByRole("button", { name: "Stop watching" }).click();
  await page.getByRole("dialog").getByRole("button", { name: answer }).click();
}

// --- Given ---

Given(
  "the company {string} is watched on {string} with board {string}",
  async ({ api }, name: string, ats: string, board: string) => {
    await api.addWatchedCompany(name, ats as Ats, board);
  },
);

Given(
  "companies {string} and {string} are watched",
  async ({ api }, first: string, second: string) => {
    for (const name of [first, second]) await api.addWatchedCompany(name);
  },
);

Given("I am on the watched companies", async ({ page }) => {
  await page.goto("/watched-companies");
});

// --- When ---

When("I open the watched companies", async ({ page }) => {
  await page.goto("/watched-companies");
});

When(
  "I watch the company {string} on {string} with board {string}",
  async ({ page }, name: string, ats: string, board: string) => {
    await page.getByRole("button", { name: "Watch a company" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel(fieldLabel("name"), { exact: true }).fill(name);
    await dialog.getByRole("combobox", { name: fieldLabel("ats") }).click();
    await page.getByRole("option", { name: ats, exact: true }).click();
    await dialog.getByLabel(fieldLabel("board"), { exact: true }).fill(board);
    await dialog.getByRole("button", { name: "Watch" }).click();
  },
);

When("I stop watching the company {string} and confirm", async ({ page }, name: string) => {
  await stopWatching(page, name, "Stop watching");
});

When("I stop watching the company {string} and cancel", async ({ page }, name: string) => {
  await stopWatching(page, name, "Cancel");
});

// --- Then ---

Then(/^I see the watched companies, in order: (".*")$/, async ({ page }, list: string) => {
  await expect(nameCells(page)).toHaveText(quoted(list));
});

Then("I see that there are no watched companies", async ({ page }) => {
  await expect(page.getByText("No watched companies", { exact: true })).toBeVisible();
  await expect(nameCells(page)).toHaveCount(0);
});

Then(
  "the watched company {string} shows {string} and {string}",
  async ({ page }, name: string, ats: string, board: string) => {
    await expect(page.getByRole("dialog")).toBeHidden();
    await expect(row(page, name).locator('[data-field="ats"]')).toHaveText(ats);
    await expect(row(page, name).locator('[data-field="board"]')).toHaveText(board);
  },
);

Then("the company is not watched", async ({ page }) => {
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(nameCells(page)).toHaveCount(0);
});
