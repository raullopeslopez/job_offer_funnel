import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { server } from "../../test/server";
import type { Application } from "./options";
import { UndoTransitionDialog } from "./UndoTransitionDialog";

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
const LATEST = `/api/v1/applications/${APPLICATION.id}/transitions/latest`;

function renderDialog() {
  const onUndone = vi.fn();
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <UndoTransitionDialog application={APPLICATION} onClose={() => {}} onUndone={onUndone} />
    </QueryClientProvider>,
  );
  return onUndone;
}

describe("UndoTransitionDialog", () => {
  it("undoes the last transition", async () => {
    // Arrange
    server.use(http.delete(LATEST, () => new HttpResponse(null, { status: 204 })));
    const onUndone = renderDialog();

    // Act
    await userEvent.click(screen.getByRole("button", { name: "Undo" }));

    // Assert
    await vi.waitFor(() => expect(onUndone).toHaveBeenCalled());
  });

  it("shows the message when the API rejects the undo", async () => {
    // Arrange
    const message = "The first stage cannot be undone; delete the application instead";
    server.use(
      http.delete(LATEST, () =>
        HttpResponse.json(
          {
            type: "/problems/invalid-transition",
            title: "Invalid transition",
            status: 409,
            detail: message,
          },
          { status: 409 },
        ),
      ),
    );
    const onUndone = renderDialog();

    // Act
    await userEvent.click(screen.getByRole("button", { name: "Undo" }));

    // Assert
    expect(await screen.findByText(message)).toBeVisible();
    expect(onUndone).not.toHaveBeenCalled();
  });
});
