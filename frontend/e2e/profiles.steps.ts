import { expect, type Locator, type Page } from "@playwright/test";
import type { DataTable } from "playwright-bdd";
import type { components } from "../src/api/schema";
import { Given, Then, When } from "./support/fixtures";
import { commaList, fieldLabel, quoted } from "./support/form";

type Syntax = components["schemas"]["Syntax"];
type WorkMode = components["schemas"]["WorkMode"];

// One Edit button per profile, labelled with its name. A CSS locator and not getByRole: an open
// dialog hides the page from the accessibility tree.
const editButtons = (page: Page) => page.locator('button[aria-label^="Edit “"]');
const profileNames = (page: Page) =>
  editButtons(page).evaluateAll((buttons) =>
    buttons.map((button) => button.getAttribute("aria-label")?.slice("Edit “".length, -1)),
  );
// Each profile is a region named after it.
const row = (page: Page, name: string): Locator => page.getByRole("region", { name, exact: true });
const rule = (page: Page, name: string, label: string) =>
  row(page, name).getByRole("group", { name: label, exact: true });
const searchesOf = (page: Page, name: string) =>
  row(page, name).getByRole("region", { name: "Generated searches" });
// The scenarios with job boards have a single profile.
const board = (page: Page, name: string) =>
  page
    .getByRole("region", { name: "Generated searches" })
    .getByRole("region", { name, exact: true });

async function expectEach(locator: Locator, list: string) {
  for (const item of commaList(list)) await expect(locator).toContainText(item);
}

async function openProfiles(page: Page) {
  await page.goto("/profiles");
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
  await row(page, name)
    .getByRole("button", { name: `Edit “${name}”` })
    .click();
  await fillProfile(page, fields);
  await page.getByRole("dialog").getByRole("button", { name: "Save" }).click();
}

// --- Given ---

Given("a search profile with:", async ({ api }, table: DataTable) => {
  const fields: Record<string, string> = table.rowsHash();
  const list = (field: string) => commaList(fields[field] ?? "");
  await api.addSearchProfile(fields.name ?? "", {
    titles: list("titles"),
    keywords: list("keywords"),
    excluded_keywords: list("excluded_keywords"),
    location: fields.location ?? null,
    work_modes: list("work_modes") as WorkMode[],
  });
});

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

Given("I am on the profiles", async ({ page }) => {
  await openProfiles(page);
});

// --- When ---

When("I open the profiles", async ({ page }) => {
  await openProfiles(page);
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
  await row(page, name)
    .getByRole("button", { name: `Delete “${name}”` })
    .click();
  await page.getByRole("dialog").getByRole("button", { name: "Delete" }).click();
});

When("I delete the profile {string} and cancel", async ({ page }, name: string) => {
  await row(page, name)
    .getByRole("button", { name: `Delete “${name}”` })
    .click();
  await page.getByRole("dialog").getByRole("button", { name: "Cancel" }).click();
});

When("I show the fit and searches of the profile {string}", async ({ page }, name: string) => {
  await row(page, name).getByRole("button", { name: "Show fit and searches" }).click();
});

// --- Then ---

Then(/^I see the profiles, in order: (".*")$/, async ({ page }, list: string) => {
  await expect.poll(() => profileNames(page)).toEqual(quoted(list));
});

Then("I see that there are no profiles", async ({ page }) => {
  await expect(page.getByText("No profiles", { exact: true })).toBeVisible();
  await expect(editButtons(page)).toHaveCount(0);
});

Then("the profile is not created", async ({ page }) => {
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(editButtons(page)).toHaveCount(0);
});

Then(
  "the profile {string} shows the titles {string}",
  async ({ page }, name: string, titles: string) => {
    await expect(page.getByRole("dialog")).toBeHidden();
    await expectEach(rule(page, name, "One of these job titles"), titles);
  },
);

Then("the profile {string} shows its fit:", async ({ page }, name: string, table: DataTable) => {
  for (const [label, values] of Object.entries(table.rowsHash())) {
    await expectEach(rule(page, name, label), values);
  }
});

Then("the profile {string} shows no location", async ({ page }, name: string) => {
  await expect(page.getByRole("dialog")).toBeHidden();
  await expect(rule(page, name, "Doable while living in")).toContainText("—");
});

Then("the profile {string} shows its fit and searches", async ({ page }, name: string) => {
  await expect(rule(page, name, "One of these job titles")).toBeVisible();
  await expect(searchesOf(page, name)).toBeVisible();
  await expect(
    row(page, name).getByRole("button", { name: "Hide fit and searches" }),
  ).toBeVisible();
});

Then("the profile {string} has its fit and searches folded", async ({ page }, name: string) => {
  await expect(
    row(page, name).getByRole("button", { name: "Show fit and searches" }),
  ).toBeVisible();
  await expect(rule(page, name, "One of these job titles")).toHaveCount(0);
  await expect(searchesOf(page, name)).toHaveCount(0);
});

Then(
  /^the job boards with searches of "(.*)" are, in order: (".*")$/,
  async ({ page }, name: string, list: string) => {
    const headings = searchesOf(page, name).getByRole("heading", { level: 4 });
    await expect(headings).toHaveText(quoted(list));
  },
);

Then(
  "{string} has {int} searches and {string} has {int}",
  async ({ page }, first: string, firstCount: number, second: string, secondCount: number) => {
    await expect(board(page, first).getByRole("link")).toHaveCount(firstCount);
    await expect(board(page, second).getByRole("link")).toHaveCount(secondCount);
  },
);

Then(
  "{string} shows the syntax {string} and {string} the syntax {string}",
  async ({ page }, first: string, firstSyntax: string, second: string, secondSyntax: string) => {
    await expect(board(page, first)).toContainText(firstSyntax);
    await expect(board(page, second)).toContainText(secondSyntax);
  },
);

Then(
  "the search {string} of {string} opens {string}",
  async ({ page }, query: string, boardName: string, url: string) => {
    const link = board(page, boardName).getByRole("link", {
      name: `Open search “${query}”`,
      exact: true,
    });
    await expect(link).toHaveAttribute("href", url);
  },
);

Then("the profile {string} says that there are no searches", async ({ page }, name: string) => {
  await expect(searchesOf(page, name)).toContainText("No searches");
  await expect(searchesOf(page, name).getByRole("link")).toHaveCount(0);
});
