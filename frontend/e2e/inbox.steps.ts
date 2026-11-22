import { expect, type Locator, type Page } from "@playwright/test";
import type { DataTable } from "playwright-bdd";
import { Given, Then, When } from "./support/fixtures";
import { fieldLabel, quoted } from "./support/form";

const STATUS_TABS = { pending: "Pending", discarded: "Discarded", promoted: "Promoted" } as const;
type Status = keyof typeof STATUS_TABS;

// The list of rows, one per offer, and the reading pane with the offer chosen.
const rows = (page: Page) => page.getByRole("region", { name: "Offer list" }).getByRole("listitem");
const titles = (page: Page) => rows(page).getByRole("button");
const rowButton = (page: Page, title: string): Locator =>
  rows(page).getByRole("button", { name: title, exact: true });
const pane = (page: Page) => page.getByRole("region", { name: "Reading pane" });
const opened = (page: Page, title: string): Locator =>
  pane(page).getByRole("article", { name: title, exact: true });

// The action bar at the foot of the reading pane.
const actionBar = (page: Page) => pane(page).getByRole("group", { name: "Offer actions" });

// The offer of a row, opened in the reading pane: the pane, with its offer and its action bar.
async function row(page: Page, title: string): Promise<Locator> {
  await rowButton(page, title).click();
  await expect(opened(page, title)).toBeVisible();
  return pane(page);
}

async function showVariants(page: Page, title: string) {
  const offer = await row(page, title);
  await offer
    .getByRole("button", { name: /more variants? of this role$/, expanded: false })
    .click();
}

// How many offers the view has: "3 to decide", "1 filtered".
const viewCount = (page: Page) => page.getByText(/^\d+ (to decide|filtered|discarded|promoted)$/);

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
  await (await row(page, title)).getByRole("button", { name: "Discard" }).click();
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

Given("I showed the variants of {string}", async ({ page }, title: string) => {
  await showVariants(page, title);
});

// --- When ---

When("I show the variants of {string}", async ({ page }, title: string) => {
  await showVariants(page, title);
});

When("I choose the row of {string}", async ({ page }, title: string) => {
  await rowButton(page, title).click();
});

Given("I chose the row of {string}", async ({ page }, title: string) => {
  await rowButton(page, title).click();
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
  await (await row(page, title)).getByRole("button", { name: "Restore" }).click();
});

When(
  "I promote the offer {string} through {string}",
  async ({ page }, title: string, channel: string) => {
    await (await row(page, title)).getByRole("button", { name: "Promote" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("combobox", { name: "Channel" }).click();
    await page.getByRole("option", { name: channel, exact: true }).click();
    await dialog.getByRole("button", { name: "Promote" }).click();
  },
);

// --- Keyboard ---

// The row button the keys go to: the focused one.
const focusedRow = (page: Page) => rows(page).locator("button:focus");
const selectedRow = (page: Page) => rows(page).locator('button[aria-current="true"]');

Given("I focus the offer list", async ({ page }) => {
  await selectedRow(page).focus();
  await expect(focusedRow(page)).toHaveCount(1);
});

// A key press goes where the focus is, so it first waits for the focus to be on a row, which
// is where the previous action leaves it, and then for what the key does.
async function press(page: Page, key: string) {
  const moves = ["j", "k", "ArrowDown", "ArrowUp"].includes(
    key.length === 1 ? key.toLowerCase() : key,
  );
  const before = moves ? await selectedRow(page).textContent() : null;
  if (key.toLowerCase() === "p" || moves || key.toLowerCase() === "d") {
    await expect(focusedRow(page)).toHaveCount(1);
  }
  await page.keyboard.press(key);
  if (moves) await expect(selectedRow(page)).not.toHaveText(before ?? "");
  if (key.toLowerCase() === "p") await expect(page.getByRole("dialog")).toBeVisible();
  if (key.toLowerCase() === "d") await expect(reasons(page)).toBeVisible();
  if (key === "Enter") {
    // Enter confirms the promotion dialog that "P" opened.
    await expect(page.getByRole("dialog")).toBeHidden();
  }
}

When("I press {string}", async ({ page }, key: string) => {
  await press(page, key);
});

When("I press {string} {int} times", async ({ page }, key: string, times: number) => {
  for (let i = 0; i < times; i++) await press(page, key);
});

When("I tab to {string} and press {string}", async ({ page }, name: string, key: string) => {
  const target = reasons(page).getByRole("button", { name, exact: true });
  for (let i = 0; i < 12 && !(await target.evaluate((el) => el === document.activeElement)); i++) {
    await page.keyboard.press("Tab");
  }
  await expect(target).toBeFocused();
  await page.keyboard.press(key);
  await expect(reasons(page)).toBeHidden();
});

Then("I see the reasons to discard", async ({ page }) => {
  await expect(reasons(page)).toBeVisible();
  await expect(reasons(page).getByRole("button").first()).toBeFocused();
});

Then("the offer {string} is still listed", async ({ page }, title: string) => {
  await expect(rowButton(page, title)).toBeVisible();
});

// --- Then ---

// A list like `"C", "B", "A"` is not one {string}: match the whole quoted list.
Then(/^I see the offers, in order: (".*")$/, async ({ page }, list: string) => {
  await expect(titles(page)).toHaveText(quoted(list));
});

Then("the row of {string} says {string}", async ({ page }, title: string, text: string) => {
  const button = page.getByRole("button", { name: title, exact: true });
  await expect(rows(page).filter({ has: button })).toContainText(text);
});

Then("no row says it has variants", async ({ page }) => {
  await expect(rows(page).filter({ hasText: /\+\d+ variants?/ })).toHaveCount(0);
});

Then("the row of {string} is selected", async ({ page }, title: string) => {
  await expect(rowButton(page, title)).toHaveAttribute("aria-current", "true");
});

Then("the action bar says {string}", async ({ page }, text: string) => {
  await expect(actionBar(page)).toContainText(text);
});

Then(
  /^the action bar has "([^"]+)" and "([^"]+)"$/,
  async ({ page }, first: string, second: string) => {
    for (const name of [first, second]) {
      await expect(actionBar(page).getByRole("button", { name, exact: true })).toBeVisible();
    }
  },
);

Then("the reading pane shows the offer {string}", async ({ page }, title: string) => {
  await expect(opened(page, title)).toBeVisible();
});

Then("the inbox says {string}", async ({ page }, heading: string) => {
  await expect(viewCount(page)).toHaveText(heading);
});

Then("I see {int} offers listed", async ({ page }, count: number) => {
  await expect(titles(page)).toHaveCount(count);
  await expect(page.getByRole("button", { name: "Show more" })).toHaveCount(0);
});

Then("the offer {string} shows {string}", async ({ page }, title: string, text: string) => {
  await expect(await row(page, title)).toContainText(text);
});

Then("the offer {string} shows no country tag", async ({ page }, title: string) => {
  await expect((await row(page, title)).getByTitle("Country")).toHaveCount(0);
});

Then("the offer {string} links to its application", async ({ page }, title: string) => {
  const offer = await row(page, title);
  await expect(offer.getByRole("link", { name: "Open application" })).toHaveAttribute(
    "href",
    /^\/applications\/[0-9a-f-]{36}$/,
  );
});

Then("I see that there are no offers", async ({ page }) => {
  await expect(page.getByText("No offers", { exact: true })).toBeVisible();
  await expect(titles(page)).toHaveCount(0);
});

Then("the offer {string} links to {string}", async ({ page }, title: string, url: string) => {
  const offer = await row(page, title);
  await expect(offer.getByRole("link", { name: "Original posting" })).toHaveAttribute("href", url);
});

Then(
  "the offer {string} shows {string} and {string}",
  async ({ page }, title: string, company: string, jobBoard: string) => {
    const offer = await row(page, title);
    await expect(offer).toContainText(company);
    await expect(offer).toContainText(jobBoard);
  },
);

Then("the offer is not added", async ({ page }) => {
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(viewCount(page)).toHaveText("0 to decide");
});

Then(
  "the {string} offers show {string} with reason {string}",
  async ({ page }, status: Status, title: string, reason: string) => {
    await page.getByRole("tab", { name: STATUS_TABS[status] }).click();
    await expect(await row(page, title)).toContainText(reason);
  },
);

Then("the {string} offers show {string}", async ({ page }, status: Status, title: string) => {
  await page.getByRole("tab", { name: STATUS_TABS[status] }).click();
  await expect(await row(page, title)).toBeVisible();
});

Then(
  "the offer keeps its title and shows the words {string}, {string} and {string} under {string}",
  async ({ page }, first: string, second: string, third: string, group: string) => {
    await expect(pane(page).getByRole("heading", { level: 3 })).toBeVisible();
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
  const offer = await row(page, title);
  await expect(offer).toBeVisible();
  await expect(offer.getByRole("button", { name: /Discard|Promote/ })).toHaveCount(0);
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

// --- On a phone ---

Given("I am on a phone", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
});

Then("no offer is open", async ({ page }) => {
  await expect(rows(page).first()).toBeVisible();
  await expect(pane(page)).toHaveCount(0);
});

Then(
  "the offer {string} is open full screen with {string}, {string} and {string}",
  async ({ page }, title: string, back: string, original: string, position: string) => {
    await expect(opened(page, title)).toBeVisible();
    await expect(pane(page).getByRole("button", { name: back, exact: true })).toBeVisible();
    await expect(pane(page).getByRole("link", { name: original })).toHaveCount(1);
    await expect(pane(page)).toContainText(position);
  },
);

Then(
  "its actions {string} and {string} are {int} px tall",
  async ({ page }, first: string, second: string, height: number) => {
    for (const name of [first, second]) {
      const box = await actionBar(page).getByRole("button", { name, exact: true }).boundingBox();
      expect(box?.height).toBeGreaterThanOrEqual(height);
    }
  },
);

When("I go back to the list", async ({ page }) => {
  await pane(page).getByRole("button", { name: "Back", exact: true }).click();
});

Then("I can undo it", async ({ page }) => {
  await expect(page.getByRole("button", { name: "Undo" })).toBeVisible();
});

Then("the reason {string} says {string}", async ({ page }, reason: string, text: string) => {
  await expect(reasons(page).getByRole("button", { name: reason, exact: true })).toContainText(
    text,
  );
});
