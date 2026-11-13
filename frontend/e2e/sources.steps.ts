import { expect, type Locator, type Page } from "@playwright/test";
import type { components } from "../src/api/schema";
import { Given, Then, When } from "./support/fixtures";
import { fieldLabel, quoted } from "./support/form";

// The @component scenarios (importing) are covered by ImportJobBoardDialog.test.tsx and
// ImportWatchedCompanyDialog.test.tsx.

type Ats = components["schemas"]["Ats"];

// A row is identified by its "Stop watching" action, whose label carries the company name.
const stopLabel = (name: string) => `Stop watching “${name}”`;
const stopButtons = (page: Page) =>
  page.getByRole("button", { name: /^Stop watching “/, includeHidden: true });
const row = (page: Page, name: string): Locator =>
  page
    .getByRole("listitem")
    .filter({ has: page.getByRole("button", { name: stopLabel(name), exact: true }) });

async function stopWatching(page: Page, name: string, answer: "Stop watching" | "Cancel") {
  await row(page, name)
    .getByRole("button", { name: stopLabel(name), exact: true })
    .click();
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

Given("I am on the sources", async ({ page }) => {
  await page.goto("/sources");
});

Given(
  "a job board named {string} imported from the RSS {string}",
  async ({ api }, name: string, template: string) => {
    await api.addRssJobBoard(name, template);
  },
);

// --- When ---

When("I open the searches of the job board {string}", async ({ page }, name: string) => {
  await page.getByRole("link", { name: `Searches of “${name}” in Profiles` }).click();
});

When("I open the sources", async ({ page }) => {
  await page.goto("/sources");
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

Then(/^I see the blocks, in order: (".*")$/, async ({ page }, list: string) => {
  await expect(page.getByRole("heading", { level: 2 })).toHaveText(quoted(list));
});

Then(
  /^the block "(.*)" lists the job boards: (".*")$/,
  async ({ page }, block: string, list: string) => {
    const edits = page.getByRole("region", { name: block }).locator('button[aria-label^="Edit “"]');
    await expect
      .poll(() => edits.evaluateAll((els) => els.map((el) => el.getAttribute("aria-label"))))
      .toEqual(quoted(list).map((name) => `Edit “${name}”`));
  },
);

Then("I see the profiles", async ({ page }) => {
  await expect(page).toHaveURL(/\/profiles$/);
});

Then(/^I see the watched companies, in order: (".*")$/, async ({ page }, list: string) => {
  await expect
    .poll(() =>
      stopButtons(page).evaluateAll((els) => els.map((el) => el.getAttribute("aria-label"))),
    )
    .toEqual(quoted(list).map(stopLabel));
});

Then("I see that there are no watched companies", async ({ page }) => {
  await expect(page.getByText("No watched companies", { exact: true })).toBeVisible();
  await expect(stopButtons(page)).toHaveCount(0);
});

Then(
  "the watched company {string} shows {string} and {string}",
  async ({ page }, name: string, ats: string, board: string) => {
    await expect(page.getByRole("dialog")).toBeHidden();
    await expect(row(page, name).getByText(ats, { exact: true })).toBeVisible();
    await expect(row(page, name).getByText(board, { exact: true })).toBeVisible();
  },
);

Then("the company is not watched", async ({ page }) => {
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(stopButtons(page)).toHaveCount(0);
});
