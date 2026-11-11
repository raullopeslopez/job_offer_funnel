import { expect, type Locator, type Page } from "@playwright/test";
import type { DataTable } from "playwright-bdd";
import { Given, Then, When } from "./support/fixtures";
import { fieldLabel, quoted } from "./support/form";

const STATUS_TABS = { pending: "Pending", discarded: "Discarded", promoted: "Promoted" } as const;
type Status = keyof typeof STATUS_TABS;

const grid = (page: Page) => page.getByRole("grid");
const titles = (page: Page) => grid(page).getByRole("link");
const row = (page: Page, title: string): Locator =>
  grid(page)
    .getByRole("row")
    .filter({ has: page.getByRole("link", { name: title, exact: true }) });

async function openInbox(page: Page, status: Status = "pending") {
  await page.goto("/inbox");
  await page.getByRole("tab", { name: STATUS_TABS[status] }).click();
}

async function addOffer(page: Page, fields: Record<string, string>) {
  await page.getByRole("button", { name: "Add offer" }).click();
  const dialog = page.getByRole("dialog");
  for (const [field, value] of Object.entries(fields)) {
    if (field === "job_board") {
      await dialog.getByRole("combobox", { name: "Job board" }).click();
      await page.getByRole("option", { name: value }).click();
    } else {
      await dialog.getByLabel(fieldLabel(field), { exact: true }).fill(value);
    }
  }
  await dialog.getByRole("button", { name: "Add" }).click();
}

async function discard(page: Page, title: string, reason?: string) {
  await row(page, title).getByRole("button", { name: "Discard" }).click();
  const dialog = page.getByRole("dialog");
  if (reason) await dialog.getByLabel("Reason").fill(reason);
  await dialog.getByRole("button", { name: "Discard" }).click();
}

// --- Given ---

Given(
  "offers for {string} as {string}, {string} and {string}, added in that order",
  async ({ api }, company: string, first: string, second: string, third: string) => {
    for (const title of [first, second, third]) await api.addOffer(company, title);
  },
);

Given("an offer for {string} as {string}", async ({ api }, company: string, title: string) => {
  await api.addOffer(company, title);
});

Given(
  "an offer for {string} as {string} with URL {string}",
  async ({ api }, company: string, title: string, url: string) => {
    await api.addOffer(company, title, url);
  },
);

Given(
  "an offer for {string} as {string} that was discarded",
  async ({ api }, company: string, title: string) => {
    const offer = await api.addOffer(company, title);
    await api.discard(offer.id);
  },
);

Given(
  "an offer for {string} as {string} that was promoted",
  async ({ api }, company: string, title: string) => {
    const offer = await api.addOffer(company, title);
    await api.promote(offer.id);
  },
);

Given("I am on the inbox", async ({ page }) => {
  await openInbox(page);
});

Given("I am on the inbox showing the {string} offers", async ({ page }, status: Status) => {
  await openInbox(page, status);
});

Given("I discarded the offer {string}", async ({ page }, title: string) => {
  await discard(page, title);
  await expect(page.getByText("Offer discarded")).toBeVisible();
});

// --- When ---

When("I open the inbox", async ({ page }) => {
  await openInbox(page);
});

When("I open the inbox showing the {string} offers", async ({ page }, status: Status) => {
  await openInbox(page, status);
});

When("I add an offer with:", async ({ page }, table: DataTable) => {
  await addOffer(page, table.rowsHash());
});

When(
  "I add an offer for {string} as {string} with URL {string}",
  async ({ page }, company: string, title: string, url: string) => {
    await addOffer(page, { url, company, title });
  },
);

When(
  "I add an offer for {string} as {string}",
  async ({ page }, company: string, title: string) => {
    await addOffer(page, { url: "https://jobs.example/2", company, title });
  },
);

When(
  "I discard the offer {string} because {string}",
  async ({ page }, title: string, reason: string) => {
    await discard(page, title, reason);
  },
);

When("I undo the discard", async ({ page }) => {
  await page.getByRole("button", { name: "Undo" }).click();
});

When("I restore the offer {string}", async ({ page }, title: string) => {
  await row(page, title).getByRole("button", { name: "Restore" }).click();
});

When(
  "I promote the offer {string} through {string}",
  async ({ page }, title: string, channel: string) => {
    await row(page, title).getByRole("button", { name: "Promote" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("combobox", { name: "Channel" }).click();
    await page.getByRole("option", { name: channel, exact: true }).click();
    await dialog.getByRole("button", { name: "Promote" }).click();
  },
);

// --- Then ---

// A list like `"C", "B", "A"` is not one {string}: match the whole quoted list.
Then(/^I see the offers, in order: (".*")$/, async ({ page }, list: string) => {
  await expect(titles(page)).toHaveText(quoted(list));
});

Then("I see {int} offers in total", async ({ page }, total: number) => {
  await expect(page.getByText(new RegExp(`^${total} offers?$`))).toBeVisible();
});

Then("I see that there are no offers", async ({ page }) => {
  await expect(page.getByText("No offers", { exact: true })).toBeVisible();
  await expect(titles(page)).toHaveCount(0);
});

Then("the offer {string} links to {string}", async ({ page }, title: string, url: string) => {
  await expect(titles(page).filter({ hasText: title })).toHaveAttribute("href", url);
});

Then(
  "the offer {string} shows {string} and {string}",
  async ({ page }, title: string, company: string, jobBoard: string) => {
    await expect(row(page, title)).toContainText(company);
    await expect(row(page, title)).toContainText(jobBoard);
  },
);

Then("the offer is not added", async ({ page }) => {
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByText("0 offers", { exact: true })).toBeVisible();
});

Then(
  "the {string} offers show {string} with reason {string}",
  async ({ page }, status: Status, title: string, reason: string) => {
    await page.getByRole("tab", { name: STATUS_TABS[status] }).click();
    await expect(row(page, title)).toContainText(reason);
  },
);

Then("the {string} offers show {string}", async ({ page }, status: Status, title: string) => {
  await page.getByRole("tab", { name: STATUS_TABS[status] }).click();
  await expect(row(page, title)).toBeVisible();
});

Then("the offer {string} cannot be discarded or promoted", async ({ page }, title: string) => {
  await expect(row(page, title)).toBeVisible();
  await expect(row(page, title).getByRole("button", { name: /Discard|Promote/ })).toHaveCount(0);
});

Then("I can import the job boards: {string}", async ({ page }, name: string) => {
  await page.getByRole("button", { name: "Import job board" }).click();
  await page.getByRole("dialog").getByRole("combobox", { name: "Job board" }).click();
  await expect(page.getByRole("option")).toHaveText([name]);
});
