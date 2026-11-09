import { expect, type Page } from "@playwright/test";
import { isoDate, shownDate } from "./support/dates";
import { Then, When } from "./support/fixtures";

// The detail of an application: moving, closing and undoing its transitions.

type Transition = { stage?: string; outcome?: string; on?: string; note?: string };

async function transition(page: Page, { stage, outcome, on, note }: Transition) {
  await page.getByRole("button", { name: stage ? "Move" : "Close", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("combobox", { name: stage ? "Stage" : "Outcome" }).click();
  await page.getByRole("option", { name: stage ?? outcome, exact: true }).click();
  if (on) await dialog.getByLabel("Date", { exact: true }).fill(isoDate(on));
  if (note) await dialog.getByLabel("Note", { exact: true }).fill(note);
  await dialog.getByRole("button", { name: stage ? "Move" : "Close", exact: true }).click();
}

async function undo(page: Page, answer: "Undo" | "Cancel") {
  await page.getByRole("button", { name: "Undo last transition" }).click();
  await page.getByRole("dialog").getByRole("button", { name: answer, exact: true }).click();
}

// --- When ---

When("I move the application to stage {string}", async ({ page }, stage: string) => {
  await transition(page, { stage });
});

When(
  "I move the application to stage {string} on {word}",
  async ({ page }, stage: string, on: string) => {
    await transition(page, { stage, on });
  },
);

When(
  "I move the application to stage {string} on {word} with the note {string}",
  async ({ page }, stage: string, on: string, note: string) => {
    await transition(page, { stage, on, note });
  },
);

When("I close the application as {string}", async ({ page }, outcome: string) => {
  await transition(page, { outcome });
});

When("I undo the last transition and confirm", async ({ page }) => {
  await undo(page, "Undo");
});

When("I undo the last transition and cancel", async ({ page }) => {
  await undo(page, "Cancel");
});

// --- Then ---

Then("I see the application in stage {string}", async ({ page }, stage: string) => {
  await expect(page.getByText(`In stage ${stage}`, { exact: true })).toBeVisible();
});

Then(
  "I see the application closed as {string} in stage {string}",
  async ({ page }, outcome: string, stage: string) => {
    await expect(page.getByRole("dialog")).toBeHidden();
    await expect(page.getByText(`Closed as ${outcome} in stage ${stage}`)).toBeVisible();
  },
);

Then("its history ends with stage {string} dated today", async ({ page }, stage: string) => {
  // Newest transition first in the timeline.
  const latest = page.getByRole("list", { name: "History" }).getByRole("listitem").first();
  await expect(latest).toHaveText(`${stage}${shownDate(isoDate("today"))}`);
});
