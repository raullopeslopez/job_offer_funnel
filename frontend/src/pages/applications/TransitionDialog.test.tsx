import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { server } from "../../test/server";
import type { Application } from "./options";
import { TransitionDialog } from "./TransitionDialog";

const APPLICATION: Application = {
  id: "6f1c1d2e-0000-4000-8000-000000000001",
  company_id: "6f1c1d2e-0000-4000-8000-0000000000a1",
  company_name: "Acme",
  role: "Backend Engineer",
  channel: "referral",
  priority: null,
  url: null,
  notes: null,
  stage: "applied",
  outcome: null,
  created_at: "2026-03-01T10:00:00Z",
};
const TRANSITIONS = `/api/v1/applications/${APPLICATION.id}/transitions`;

function renderDialog(mode: "move" | "close") {
  const onSaved = vi.fn();
  render(
    <TransitionDialog application={APPLICATION} mode={mode} onClose={() => {}} onSaved={onSaved} />,
  );
  return onSaved;
}

async function choose(label: string, option: string) {
  const user = userEvent.setup();
  await user.click(screen.getByRole("combobox", { name: label }));
  await user.click(screen.getByRole("option", { name: option }));
  return user;
}

describe("TransitionDialog", () => {
  it.each([
    ["move", "Stage", "screening", { to_stage: "screening" }],
    ["close", "Outcome", "rejected", { outcome: "rejected" }],
  ] as const)(
    "%s sends the choice, with an empty date and note as null",
    async (mode, label, option, target) => {
      // Arrange
      let body: unknown;
      server.use(
        http.post(TRANSITIONS, async ({ request }) => {
          body = await request.json();
          return HttpResponse.json({}, { status: 201 });
        }),
      );
      const onSaved = renderDialog(mode);

      // Act
      const user = await choose(label, option);
      await user.click(screen.getByRole("button", { name: mode === "move" ? "Move" : "Close" }));

      // Assert
      expect(body).toEqual({ ...target, occurred_on: null, note: null });
      expect(onSaved).toHaveBeenCalled();
    },
  );

  // specs/ui/stage_transitions.feature: a rejected transition is shown as a message.
  // A future date depends on today, so the E2E leaves it to this test.
  it("shows the message of a transition the API rejects", async () => {
    // Arrange
    server.use(
      http.post(TRANSITIONS, () =>
        HttpResponse.json(
          {
            type: "/problems/invalid-transition-date",
            title: "Invalid transition date",
            status: 409,
            detail: "2026-03-11 is in the future",
          },
          { status: 409 },
        ),
      ),
    );
    const onSaved = renderDialog("move");

    // Act
    const user = await choose("Stage", "screening");
    await user.type(screen.getByLabelText("Date"), "2026-03-11");
    await user.click(screen.getByRole("button", { name: "Move" }));

    // Assert
    expect(await screen.findByText("2026-03-11 is in the future")).toBeVisible();
    expect(onSaved).not.toHaveBeenCalled();
  });

  it("shows a validation error next to its field", async () => {
    // Arrange
    server.use(
      http.post(TRANSITIONS, () =>
        HttpResponse.json(
          {
            type: "/problems/validation-error",
            title: "Request validation failed",
            status: 422,
            errors: [{ field: "body.note", message: "Too long" }],
          },
          { status: 422 },
        ),
      ),
    );
    renderDialog("move");

    // Act
    const user = await choose("Stage", "screening");
    await user.click(screen.getByRole("button", { name: "Move" }));

    // Assert
    expect(await screen.findByText("Too long")).toBeVisible();
    expect(screen.getByLabelText("Note")).toHaveAttribute("aria-invalid", "true");
  });
});
