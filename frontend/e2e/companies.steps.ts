import { expect, type Locator, type Page } from "@playwright/test";
import type { DataTable } from "playwright-bdd";
import { Given, Then, When } from "./support/fixtures";
import { fieldLabel, quoted } from "./support/form";

// Companies (specs/ui/companies.feature) and job boards (specs/ui/sources.feature) work alike;
// the sources screen is opened by sources.steps.ts.
type Section = "companies" | "job boards";
const NEW_BUTTONS: Record<Section, string> = {
  companies: "New company",
  "job boards": "New job board",
};
const SELECTS = new Set(["syntax", "feed"]);

// Every company or job board has an Edit button labelled with its name.
const editButtons = (page: Page) => page.locator('button[aria-label^="Edit “"]');
// A company is a row of the grid; a job board, an item of its block on the sources.
const row = (page: Page, name: string): Locator =>
  page
    .locator('[role="grid"] [role="row"], li')
    .filter({ has: page.getByText(name, { exact: true }) });

async function fill(page: Page, fields: Record<string, string>) {
  const dialog = page.getByRole("dialog");
  for (const [field, value] of Object.entries(fields)) {
    if (SELECTS.has(field)) {
      await dialog.getByRole("combobox", { name: fieldLabel(field) }).click();
      await page.getByRole("option", { name: value, exact: true }).click();
    } else {
      await dialog.getByLabel(fieldLabel(field), { exact: true }).fill(value);
    }
  }
}

async function create(page: Page, section: Section, fields: Record<string, string>) {
  await page.getByRole("button", { name: NEW_BUTTONS[section] }).click();
  await fill(page, fields);
  await page.getByRole("dialog").getByRole("button", { name: "Create" }).click();
}

async function edit(page: Page, name: string, fields: Record<string, string>) {
  await row(page, name)
    .getByRole("button", { name: /^Edit /u })
    .click();
  await fill(page, fields);
  await page.getByRole("dialog").getByRole("button", { name: "Save" }).click();
}

async function remove(page: Page, name: string, answer: "Delete" | "Cancel") {
  await row(page, name)
    .getByRole("button", { name: /^Delete /u })
    .click();
  await page.getByRole("dialog").getByRole("button", { name: answer }).click();
}

// --- Given ---

Given("companies named {string} and {string}", async ({ api }, first: string, second: string) => {
  for (const name of [first, second]) await api.addCompany(name);
});

Given(
  "companies named {string}, {string} and {string}",
  async ({ api }, first: string, second: string, third: string) => {
    for (const name of [first, second, third]) await api.addCompany(name);
  },
);

Given(
  "a company named {string} with website {string}",
  async ({ api }, name: string, website: string) => {
    await api.addCompany(name, website);
  },
);

Given("the company {string} has an application", async ({ api }, company: string) => {
  await api.addApplication(company, "Backend Engineer");
});

Given("job boards named {string} and {string}", async ({ api }, first: string, second: string) => {
  for (const name of [first, second]) await api.addJobBoard(name);
});

Given(
  "job boards named {string}, {string} and {string}",
  async ({ api }, first: string, second: string, third: string) => {
    for (const name of [first, second, third]) await api.addJobBoard(name);
  },
);

Given("I am on the companies", async ({ page }) => {
  await page.goto("/companies");
});

// --- When ---

When("I open the companies", async ({ page }) => {
  await page.goto("/companies");
});

When(
  "I create a company named {string} with website {string}",
  async ({ page }, name: string, website: string) => {
    await create(page, "companies", { name, website });
  },
);

When("I create a job board with:", async ({ page }, table: DataTable) => {
  await create(page, "job boards", table.rowsHash());
});

When(
  "I create a job board named {string} with template {string} and syntax {string}",
  async ({ page }, name: string, template: string, syntax: string) => {
    await create(page, "job boards", { name, search_url_template: template, syntax });
  },
);

When(
  /^I change the "(.*)" of the (?:company|job board) "(.*)" to "(.*)"$/,
  async ({ page }, field: string, name: string, value: string) => {
    await edit(page, name, { [field]: value });
  },
);

When(
  "I change the job board {string} to be imported from the feed {string}",
  async ({ page }, name: string, feed: string) => {
    await edit(page, name, { feed });
  },
);

When(
  "I change the job board {string} to be imported from the RSS {string}",
  async ({ page }, name: string, template: string) => {
    await edit(page, name, { feed: "rss", rss_url_template: template });
  },
);

When(
  "I change the job board {string} to be imported from the email alert {string}",
  async ({ page }, name: string, emailAlert: string) => {
    await edit(page, name, { feed: `${emailAlert} alerts` });
  },
);

When(
  "I clear the {string} of the company {string}",
  async ({ page }, field: string, name: string) => {
    await edit(page, name, { [field]: "" });
  },
);

When(/^I delete the (?:company|job board) "(.*)" and confirm$/, async ({ page }, name: string) => {
  await remove(page, name, "Delete");
});

When(/^I delete the (?:company|job board) "(.*)" and cancel$/, async ({ page }, name: string) => {
  await remove(page, name, "Cancel");
});

// --- Then ---

Then(/^I see the (?:companies|job boards), in order: (".*")$/, async ({ page }, list: string) => {
  // The name cell also holds the avatar initial and a second line: read the names from the
  // Edit buttons, one per row, labelled with the name. On the sources, the blocks keep the
  // job boards of each import method alphabetically.
  const names = () =>
    editButtons(page).evaluateAll((buttons) =>
      buttons.map((button) => button.getAttribute("aria-label")?.slice("Edit “".length, -1)),
    );
  await expect.poll(names).toEqual(quoted(list));
});

Then("I see that there are no companies", async ({ page }) => {
  await expect(page.getByText("No companies", { exact: true })).toBeVisible();
  await expect(editButtons(page)).toHaveCount(0);
});

Then("I see that there are no job boards", async ({ page }) => {
  // Each block of job boards says so.
  await expect(page.getByText("No job boards", { exact: true })).toHaveCount(4);
  await expect(editButtons(page)).toHaveCount(0);
});

Then(/^the (?:company|job board) is not created$/, async ({ page }) => {
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(editButtons(page)).toHaveCount(0);
});

Then(
  /^the (?:company|job board) "(.*)" shows "(.*)"$/,
  async ({ page }, name: string, text: string) => {
    await expect(page.getByRole("dialog")).toBeHidden();
    await expect(row(page, name)).toContainText(text);
  },
);

Then("the company {string} shows no website", async ({ page }, name: string) => {
  await expect(page.getByRole("dialog")).toBeHidden();
  await expect(row(page, name).locator('[data-field="name"]')).toHaveText(/\n—$/u, {
    useInnerText: true,
  });
});
