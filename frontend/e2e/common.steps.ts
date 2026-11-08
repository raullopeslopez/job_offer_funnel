import { expect } from "@playwright/test";
import { E2E_TOKEN } from "./support/env";
import { Given, Then } from "./support/fixtures";
import { fieldLabel } from "./support/form";

// Steps shared by more than one screen.

Given("I am signed in with a valid token", async ({ page, api }) => {
  expect(api).toBeDefined(); // requesting `api` resets the database
  await page.addInitScript((token) => localStorage.setItem("funnel.authToken", token), E2E_TOKEN);
});

Given("a job board named {string}", async ({ api }, name: string) => {
  await api.addJobBoard(name);
});

Then("I see an error on the field {string}", async ({ page }, field: string) => {
  const input = page.getByRole("dialog").getByLabel(fieldLabel(field), { exact: true });
  await expect(input).toHaveAttribute("aria-invalid", "true");
});

Then("I see the message {string}", async ({ page }, message: string) => {
  await expect(page.getByText(message)).toBeVisible();
});
