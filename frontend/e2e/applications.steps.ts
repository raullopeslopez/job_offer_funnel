import { expect, type Locator, type Page } from "@playwright/test";
import type { DataTable } from "playwright-bdd";
import type { components } from "../src/api/schema";
import { isoDate, shownDate } from "./support/dates";
import { Given, Then, When } from "./support/fixtures";
import { fieldLabel, quoted } from "./support/form";

type Schemas = components["schemas"];
type Stage = Schemas["Stage"];
type Outcome = Schemas["Outcome"];
type Channel = Schemas["Channel"];

const FILTER_LABELS: Record<string, string> = {
  stage: "Stage",
  outcome: "Outcome",
  channel: "Channel",
  status: "Status",
};
const SELECTS = new Set(["company", "channel", "priority", "stage"]);
const NONEXISTENT_ID = "00000000-0000-4000-8000-000000000000";

const grid = (page: Page) => page.getByRole("grid");
const roles = (page: Page) => grid(page).getByRole("link");
const row = (page: Page, role: string): Locator =>
  grid(page)
    .getByRole("row")
    .filter({ has: page.getByRole("link", { name: role, exact: true }) });
const detailField = (page: Page, label: string) => page.locator(`dt:text-is("${label}") + dd`);

async function openApplications(page: Page) {
  await page.goto("/applications");
}

async function openApplication(page: Page, id: string) {
  await page.goto(`/applications/${id}`);
}

async function filterBy(page: Page, filter: string, value: string) {
  await page.getByRole("combobox", { name: FILTER_LABELS[filter] ?? filter }).click();
  await page.getByRole("option", { name: value, exact: true }).click();
}

async function fillApplication(page: Page, fields: Record<string, string>) {
  const dialog = page.getByRole("dialog");
  for (const [field, value] of Object.entries(fields)) {
    if (SELECTS.has(field)) {
      await dialog.getByRole("combobox", { name: fieldLabel(field) }).click();
      await page.getByRole("option", { name: value, exact: true }).click();
    } else {
      const text = field === "occurred_on" ? isoDate(value) : value;
      await dialog.getByLabel(fieldLabel(field), { exact: true }).fill(text);
    }
  }
}

async function editApplication(page: Page, fields: Record<string, string>) {
  await page.getByRole("button", { name: "Edit" }).click();
  await fillApplication(page, fields);
  await page.getByRole("dialog").getByRole("button", { name: "Save" }).click();
}

// --- Given ---

Given("a company named {string}", async ({ api }, name: string) => {
  await api.addCompany(name);
});

Given("an application for {string} as {string}", async ({ api }, company: string, role: string) => {
  await api.addApplication(company, role);
});

Given(
  "applications for {string} as {string} and {string}, created in that order",
  async ({ api }, company: string, first: string, second: string) => {
    for (const role of [first, second]) await api.addApplication(company, role);
  },
);

Given(
  "applications for {string} as {string}, {string} and {string}, created in that order",
  async ({ api }, company: string, first: string, second: string, third: string) => {
    for (const role of [first, second, third]) await api.addApplication(company, role);
  },
);

Given(
  "an application for {string} as {string} via {string} in stage {string}",
  async ({ api }, company: string, role: string, channel: Channel, stage: Stage) => {
    await api.addApplication(company, role, { channel, stage: stage as "evaluated" | "applied" });
  },
);

Given(
  "an application for {string} as {string} closed as {string}",
  async ({ api }, company: string, role: string, outcome: Outcome) => {
    // Not every outcome closes an evaluated application: start it as applied.
    const application = await api.addApplication(company, role, { stage: "applied" });
    await api.transition(application.id, { outcome });
  },
);

Given(
  "an application for {string} as {string} with notes {string}",
  async ({ api }, company: string, role: string, notes: string) => {
    await api.addApplication(company, role, { notes });
  },
);

Given(
  "an application for {string} as {string} in stage {string} since {word}",
  async ({ api }, company: string, role: string, stage: Stage, since: string) => {
    // An application starts as evaluated or applied; later stages are reached by moving it.
    const first = stage === "evaluated" ? "evaluated" : "applied";
    const application = await api.addApplication(company, role, {
      stage: first,
      occurred_on: since,
    });
    if (stage !== first) {
      await api.transition(application.id, { to_stage: stage, occurred_on: since });
    }
  },
);

Given("it was moved to stage {string} on {word}", async ({ api }, stage: Stage, on: string) => {
  await api.transition(api.lastApplicationId, { to_stage: stage, occurred_on: on });
});

Given("it was closed as {string} on {word}", async ({ api }, outcome: Outcome, on: string) => {
  await api.transition(api.lastApplicationId, { outcome, occurred_on: on });
});

// Later stages and outcomes are reached through transitions, as the user would.
Given(
  "these applications for {string}, created in this order:",
  async ({ api }, company: string, table: DataTable) => {
    for (const { role = "", stage, outcome, channel } of table.hashes()) {
      const application = await api.addApplication(company, role, {
        channel: channel as Channel,
        stage: "applied",
      });
      if (stage && stage !== "applied") {
        await api.transition(application.id, { to_stage: stage as Stage });
      }
      if (outcome) await api.transition(application.id, { outcome: outcome as Outcome });
    }
  },
);

Given("I am on the applications", async ({ page }) => {
  await openApplications(page);
});

Given("I am on the application {string}", async ({ page, api }, role: string) => {
  await openApplication(page, api.applicationIds.get(role) ?? NONEXISTENT_ID);
});

// --- When ---

When("I open the applications", async ({ page }) => {
  await openApplications(page);
});

When(
  "I filter the applications by {string} {string}",
  async ({ page }, filter: string, value: string) => {
    await filterBy(page, filter, value);
  },
);

When(
  "I filter the applications by stage {string} and channel {string}",
  async ({ page }, stage: string, channel: string) => {
    await filterBy(page, "stage", stage);
    await filterBy(page, "channel", channel);
  },
);

When("I create an application with:", async ({ page }, table: DataTable) => {
  await page.getByRole("button", { name: "New application" }).click();
  await fillApplication(page, table.rowsHash());
  await page.getByRole("dialog").getByRole("button", { name: "Create" }).click();
});

When("I open the application {string}", async ({ page }, role: string) => {
  await roles(page).getByText(role, { exact: true }).click();
});

When("I open an application that does not exist", async ({ page }) => {
  await openApplication(page, NONEXISTENT_ID);
});

When("I edit the application with:", async ({ page }, table: DataTable) => {
  await editApplication(page, table.rowsHash());
});

When("I clear the {string} of the application", async ({ page }, field: string) => {
  await editApplication(page, { [field]: "" });
});

When("I delete the application and confirm", async ({ page }) => {
  await page.getByRole("button", { name: "Delete" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Delete" }).click();
});

When("I delete the application and cancel", async ({ page }) => {
  await page.getByRole("button", { name: "Delete" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Cancel" }).click();
});

// --- Then ---

Then(/^I see the applications, in order: (".*")$/, async ({ page }, list: string) => {
  await expect(roles(page)).toHaveText(quoted(list));
});

Then("I see {int} applications in total", async ({ page }, total: number) => {
  await expect(page.getByText(new RegExp(`^${total} applications?$`))).toBeVisible();
});

Then("I see that there are no applications", async ({ page }) => {
  await expect(page.getByText("No applications", { exact: true })).toBeVisible();
  await expect(roles(page)).toHaveCount(0);
});

Then("the application is not created", async ({ page }) => {
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(roles(page)).toHaveCount(0);
});

Then("the application {string} shows {string}", async ({ page }, role: string, text: string) => {
  await expect(row(page, role)).toContainText(text);
});

Then(
  "the application {string} shows {string}, {string} and {string}",
  async ({ page }, role: string, first: string, second: string, third: string) => {
    for (const text of [first, second, third]) await expect(row(page, role)).toContainText(text);
  },
);

Then(
  "I see the application {string} at {string}",
  async ({ page }, role: string, company: string) => {
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(role);
    await expect(page.getByText(`at ${company}`, { exact: true })).toBeVisible();
  },
);

Then(
  "I see the application {string} at {string}, closed as {string} in stage {string}",
  async ({ page }, role: string, company: string, outcome: string, stage: string) => {
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(role);
    await expect(page.getByText(`at ${company}`, { exact: true })).toBeVisible();
    await expect(page.getByText(`Closed as ${outcome} in stage ${stage}`)).toBeVisible();
  },
);

Then("I see its history:", async ({ page }, table: DataTable) => {
  const rows = page.getByRole("list", { name: "History" }).getByRole("listitem");
  // The timeline shows the newest transition first; the spec lists them oldest first.
  const expected = table
    .hashes()
    .map(({ stage = "", outcome = "", occurred_on = "", note = "" }) =>
      [stage, outcome, shownDate(occurred_on), note].join(""),
    )
    .reverse();
  await expect(rows).toHaveText(expected);
});

Then("it shows the notes {string}", async ({ page }, notes: string) => {
  await expect(page.getByRole("dialog")).toBeHidden();
  await expect(detailField(page, "Notes")).toHaveText(notes);
});

Then("it shows no notes", async ({ page }) => {
  await expect(page.getByRole("dialog")).toBeHidden();
  await expect(detailField(page, "Notes")).toHaveText("—");
});
