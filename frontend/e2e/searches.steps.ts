import { expect, type Locator, type Page } from "@playwright/test";
import type { DataTable } from "playwright-bdd";
import type { components } from "../src/api/schema";
import { Given, Then, When } from "./support/fixtures";
import { commaList, fieldLabel, quoted } from "./support/form";

type Syntax = components["schemas"]["Syntax"];
type WorkMode = components["schemas"]["WorkMode"];

const grid = (page: Page) => page.getByRole("grid");
// DataGrid marks each cell with its column; no role tells the name cells apart. Not under
// getByRole("grid"): an open dialog hides the grid from the accessibility tree.
const nameCells = (page: Page) => page.locator('[role="gridcell"][data-field="name"]');
const row = (page: Page, name: string): Locator =>
  grid(page)
    .getByRole("row")
    .filter({ has: page.getByRole("gridcell", { name, exact: true }) });
const board = (page: Page, name: string) =>
  page.getByRole("dialog").getByRole("region", { name, exact: true });

async function openSearches(page: Page) {
  await page.goto("/searches");
}

async function fillProfile(page: Page, fields: Record<string, string>) {
  const dialog = page.getByRole("dialog");
  for (const [field, value] of Object.entries(fields)) {
    if (field === "work_modes") {
      await dialog.getByRole("combobox", { name: "Work modes" }).click();
      for (const mode of commaList(value)) {
        await page.getByRole("option", { name: mode, exact: true }).click();
      }
      await page.keyboard.press("Escape");
    } else {
      await dialog.getByLabel(fieldLabel(field), { exact: true }).fill(value);
    }
  }
}

async function createProfile(page: Page, fields: Record<string, string>) {
  await page.getByRole("button", { name: "New profile" }).click();
  await fillProfile(page, fields);
  await page.getByRole("dialog").getByRole("button", { name: "Create" }).click();
}

async function editProfile(page: Page, name: string, fields: Record<string, string>) {
  await row(page, name).getByRole("button", { name: "Edit" }).click();
  await fillProfile(page, fields);
  await page.getByRole("dialog").getByRole("button", { name: "Save" }).click();
}

// --- Given ---

Given("a search profile named {string}", async ({ api }, name: string) => {
  await api.addSearchProfile(name);
});

Given(
  "search profiles named {string} and {string}",
  async ({ api }, first: string, second: string) => {
    for (const name of [first, second]) await api.addSearchProfile(name);
  },
);

Given(
  "search profiles named {string}, {string} and {string}",
  async ({ api }, first: string, second: string, third: string) => {
    for (const name of [first, second, third]) await api.addSearchProfile(name);
  },
);

Given(
  "a search profile named {string} with location {string}",
  async ({ api }, name: string, location: string) => {
    await api.addSearchProfile(name, { location });
  },
);

Given(
  "a search profile named {string} with titles {string}",
  async ({ api }, name: string, titles: string) => {
    await api.addSearchProfile(name, { titles: commaList(titles) });
  },
);

Given(
  "a search profile named {string} with titles {string} and work modes {string}",
  async ({ api }, name: string, titles: string, workModes: string) => {
    await api.addSearchProfile(name, {
      titles: commaList(titles),
      work_modes: commaList(workModes) as WorkMode[],
    });
  },
);

Given(
  "a job board named {string} with syntax {string}",
  async ({ api }, name: string, syntax: Syntax) => {
    await api.addJobBoard(name, syntax);
  },
);

Given(
  "a job board named {string} with syntax {string} and template {string}",
  async ({ api }, name: string, syntax: Syntax, template: string) => {
    await api.addJobBoard(name, syntax, template);
  },
);

Given("I am on the searches", async ({ page }) => {
  await openSearches(page);
});

// --- When ---

When("I open the searches", async ({ page }) => {
  await openSearches(page);
});

When("I create a profile with:", async ({ page }, table: DataTable) => {
  await createProfile(page, table.rowsHash());
});

When(
  "I create a profile named {string} with titles {string}",
  async ({ page }, name: string, titles: string) => {
    await createProfile(page, { name, titles });
  },
);

When(
  "I change the {string} of the profile {string} to {string}",
  async ({ page }, field: string, name: string, value: string) => {
    await editProfile(page, name, { [field]: value });
  },
);

When(
  "I clear the {string} of the profile {string}",
  async ({ page }, field: string, name: string) => {
    await editProfile(page, name, { [field]: "" });
  },
);

When("I delete the profile {string} and confirm", async ({ page }, name: string) => {
  await row(page, name).getByRole("button", { name: "Delete" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Delete" }).click();
});

When("I delete the profile {string} and cancel", async ({ page }, name: string) => {
  await row(page, name).getByRole("button", { name: "Delete" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Cancel" }).click();
});

When("I open the searches of the profile {string}", async ({ page }, name: string) => {
  await row(page, name).getByRole("button", { name: "Searches" }).click();
});

// --- Then ---

Then(/^I see the profiles, in order: (".*")$/, async ({ page }, list: string) => {
  await expect(nameCells(page)).toHaveText(quoted(list));
});

Then("I see that there are no profiles", async ({ page }) => {
  await expect(page.getByText("No profiles", { exact: true })).toBeVisible();
  await expect(nameCells(page)).toHaveCount(0);
});

Then("the profile is not created", async ({ page }) => {
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(nameCells(page)).toHaveCount(0);
});

Then("the profile {string} shows {string}", async ({ page }, name: string, text: string) => {
  await expect(row(page, name)).toContainText(text);
});

Then("the profile {string} shows no location", async ({ page }, name: string) => {
  await expect(page.getByRole("dialog")).toBeHidden();
  await expect(row(page, name).locator('[data-field="location"]')).toHaveText("");
});

Then(/^the job boards with searches are, in order: (".*")$/, async ({ page }, list: string) => {
  const headings = page.getByRole("dialog").getByRole("heading", { level: 3 });
  await expect(headings).toHaveText(quoted(list));
});

Then(
  "{string} has {int} searches and {string} has {int}",
  async ({ page }, first: string, firstCount: number, second: string, secondCount: number) => {
    await expect(board(page, first).getByRole("link")).toHaveCount(firstCount);
    await expect(board(page, second).getByRole("link")).toHaveCount(secondCount);
  },
);

Then("I see that the work modes to filter by are {string}", async ({ page }, workModes: string) => {
  await expect(page.getByRole("dialog")).toContainText(`Filter by work mode: ${workModes}`);
});

Then(
  "the search {string} of {string} links to {string}",
  async ({ page }, query: string, boardName: string, url: string) => {
    const link = board(page, boardName).getByRole("link", { name: query, exact: true });
    await expect(link).toHaveAttribute("href", url);
  },
);

Then("I see that there are no searches", async ({ page }) => {
  await expect(page.getByRole("dialog")).toContainText("No searches");
  await expect(page.getByRole("dialog").getByRole("link")).toHaveCount(0);
});
