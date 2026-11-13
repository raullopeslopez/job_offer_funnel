import { expect, type Page } from "@playwright/test";
import type { DataTable } from "playwright-bdd";
import type { components } from "../src/api/schema";
import { Given, Then, When } from "./support/fixtures";

// The metrics screen: conversion by stage and by channel, and the active pipeline.

type Schemas = components["schemas"];

async function expectConversion(page: Page, name: string, table: DataTable) {
  const rows = page.getByRole("table", { name }).locator("tbody tr");
  const expected = table
    .hashes()
    .map(({ from = "", to = "", reached_from = "", reached_to = "", rate = "" }) =>
      [from, to, reached_from, reached_to, rate].join(""),
    );
  await expect(rows).toHaveText(expected);
}

// --- Given ---

// An application starts as evaluated or applied; later stages and outcomes are
// reached through transitions, as the user would.
Given("these applications for {string}:", async ({ api }, company: string, table: DataTable) => {
  for (const [index, { stage, outcome, channel }] of table.hashes().entries()) {
    const first = stage === "evaluated" ? "evaluated" : "applied";
    const application = await api.addApplication(company, `Role ${index + 1}`, {
      channel: channel as Schemas["Channel"],
      stage: first,
    });
    if (stage !== first) {
      await api.transition(application.id, { to_stage: stage as Schemas["Stage"] });
    }
    if (outcome) {
      await api.transition(application.id, { outcome: outcome as Schemas["Outcome"] });
    }
  }
});

// --- When ---

When("I open the metrics", async ({ page }) => {
  await page.goto("/metrics?view=funnel");
  await expect(page.getByRole("heading", { name: "Metrics", level: 1 })).toBeVisible();
});

// --- Then ---

Then("I see the conversion by stage:", async ({ page }, table: DataTable) => {
  await expectConversion(page, "Conversion by stage", table);
});

Then(
  "I see the channels, in order: {string}, {string}",
  async ({ page }, first: string, second: string) => {
    const headings = page
      .getByRole("region", { name: "Conversion by channel" })
      .getByRole("heading", { level: 3 });
    await expect(headings).toHaveText([first, second]);
  },
);

Then(
  "I see the conversion for channel {string}:",
  async ({ page }, channel: string, table: DataTable) => {
    await expectConversion(page, `Conversion for ${channel}`, table);
  },
);

Then("I see the active pipeline:", async ({ page }, table: DataTable) => {
  const rows = page.getByRole("table", { name: "Active pipeline" }).locator("tbody tr");
  const expected = table.hashes().map(({ stage = "", applications = "" }) => stage + applications);
  await expect(rows).toHaveText(expected);
});

Then("I see {int} active applications in total", async ({ page }, total: number) => {
  await expect(page.getByText(`${total} active applications in total`)).toBeVisible();
});
