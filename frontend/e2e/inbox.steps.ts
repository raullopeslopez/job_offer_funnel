import { expect, type Locator, type Page } from "@playwright/test";
import type { DataTable } from "playwright-bdd";
import { Given, Then, When } from "./support/fixtures";
import { fieldLabel, quoted } from "./support/form";

const STATUS_TABS = { pending: "Pending", discarded: "Discarded", promoted: "Promoted" } as const;
type Status = keyof typeof STATUS_TABS;

const pieces = (page: Page) => page.getByRole("article");
const titles = (page: Page) => pieces(page).getByRole("heading", { level: 3 }).getByRole("link");
const row = (page: Page, title: string): Locator =>
  page.getByRole("article", { name: title, exact: true });

const variantGroup = (page: Page, name: string): Locator =>
  page.getByRole("region", { name, exact: true });

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

const reasons = (page: Page) => page.getByRole("group", { name: "Discard because" });

async function startDiscarding(page: Page, title: string) {
  await row(page, title).getByRole("button", { name: "Discard" }).click();
}

const titleWords = (page: Page) =>
  reasons(page).getByRole("group", { name: "A word in the title" });

async function discard(page: Page, title: string, reason: string) {
  await startDiscarding(page, title);
  await reasons(page).getByRole("button", { name: reason, exact: true }).click();
}

async function discardByWord(page: Page, title: string, word: string) {
  await startDiscarding(page, title);
  await titleWords(page).getByRole("button", { name: word, exact: true }).click();
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

Given("{int} offers for {string}", async ({ api }, count: number, company: string) => {
  for (let i = 1; i <= count; i++) {
    await api.addOffer(company, `Offer ${i}`, `https://jobs.example/${i}`);
  }
});

Given("I am on the inbox", async ({ page }) => {
  await openInbox(page);
});

Given("I am on the inbox showing the {string} offers", async ({ page }, status: Status) => {
  await openInbox(page, status);
});

Given(
  "I discarded the offer {string} because {string}",
  async ({ page }, title: string, reason: string) => {
    await discard(page, title, reason);
    await expect(page.getByText("Offer discarded")).toBeVisible();
  },
);

Given("I started discarding the offer {string}", async ({ page }, title: string) => {
  await startDiscarding(page, title);
  await expect(reasons(page)).toBeVisible();
});

Given("I showed the group of variants {string}", async ({ page }, group: string) => {
  await variantGroup(page, group).getByRole("button", { expanded: false }).click();
});

// --- When ---

When("I show the group of variants {string}", async ({ page }, group: string) => {
  await variantGroup(page, group).getByRole("button", { expanded: false }).click();
});

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
    await addOffer(page, {
      url: `https://jobs.example/added/${encodeURIComponent(title)}`,
      company,
      title,
    });
  },
);

When(
  "I discard the offer {string} because {string}",
  async ({ page }, title: string, reason: string) => {
    await discard(page, title, reason);
  },
);

When(
  "I discard the offer {string} because of the word {string}",
  async ({ page }, title: string, word: string) => {
    await discardByWord(page, title, word);
  },
);

When("I start discarding the offer {string}", async ({ page }, title: string) => {
  await startDiscarding(page, title);
});

When("I cancel the discard", async ({ page }) => {
  await reasons(page).getByRole("button", { name: "Cancel" }).click();
});

When("I ask to see more offers", async ({ page }) => {
  await expect(titles(page)).toHaveCount(20);
  await page.getByRole("button", { name: "Show more" }).click();
});

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

Then("I see the group of variants {string}", async ({ page }, group: string) => {
  await expect(variantGroup(page, group)).toBeVisible();
});

Then("I see no group of variants", async ({ page }) => {
  await expect(page.getByRole("region", { name: / variants$/ })).toHaveCount(0);
});

Then("the inbox says {string}", async ({ page }, heading: string) => {
  await expect(page.getByRole("heading", { level: 1, includeHidden: true })).toHaveText(heading);
});

Then("I see {int} offers listed", async ({ page }, count: number) => {
  await expect(titles(page)).toHaveCount(count);
  await expect(page.getByRole("button", { name: "Show more" })).toHaveCount(0);
});

Then("the offer {string} shows {string}", async ({ page }, title: string, text: string) => {
  await expect(row(page, title)).toContainText(text);
});

Then("the offer {string} shows no country tag", async ({ page }, title: string) => {
  await expect(row(page, title).getByTitle("Country")).toHaveCount(0);
});

Then("the offer {string} links to its application", async ({ page }, title: string) => {
  await expect(row(page, title).getByRole("link", { name: "View application" })).toHaveAttribute(
    "href",
    /^\/applications\/[0-9a-f-]{36}$/,
  );
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
  await expect(page.getByRole("heading", { level: 1, includeHidden: true })).toHaveText(
    "0 to decide",
  );
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

Then(
  "the offer keeps its title and shows the words {string}, {string} and {string} under {string}",
  async ({ page }, first: string, second: string, third: string, group: string) => {
    await expect(pieces(page).getByRole("heading", { level: 3 }).getByRole("link")).toBeVisible();
    const words = reasons(page).getByRole("group", { name: group });
    await expect(words.getByRole("button")).toHaveText([first, second, third]);
  },
);

// A list like `"A", "B" and "C"` is not one {string}: match the whole quoted list.
Then(
  /^it shows "([^"]+)" with the reasons (".*")$/,
  async ({ page }, label: string, list: string) => {
    // The reasons are named by their label; on a wide screen they show only that.
    const others = page.getByRole("group", { name: label }).locator("button[aria-label]");
    await expect(others).toHaveText(quoted(list), { useInnerText: true });
  },
);

Then("the offer shows no reasons", async ({ page }) => {
  await expect(reasons(page)).toHaveCount(0);
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

Then(/^there is no "([^"]+)"$/, async ({ page }, name: string) => {
  await expect(titles(page).first()).toBeVisible();
  await expect(page.getByRole("button", { name })).toHaveCount(0);
});
