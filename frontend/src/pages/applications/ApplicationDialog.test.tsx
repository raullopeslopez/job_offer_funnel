import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { server } from "../../test/server";
import { ApplicationDialog } from "./ApplicationDialog";
import type { Application } from "./options";

const ACME = { id: "6f1c1d2e-0000-4000-8000-0000000000a1", name: "Acme", website: null };

const APPLICATION: Application = {
  id: "6f1c1d2e-0000-4000-8000-000000000001",
  company_id: ACME.id,
  company_name: "Acme",
  role: "Backend Engineer",
  channel: "referral",
  priority: "high",
  url: "https://acme.example/jobs/1",
  notes: "Call back",
  stage: "applied",
  outcome: null,
  created_at: "2026-03-01T10:00:00Z",
};

function renderDialog(application: Application | null = null) {
  server.use(
    http.get("/api/v1/companies", () =>
      HttpResponse.json({ items: [ACME], total: 1, limit: 100, offset: 0 }),
    ),
  );
  const onSaved = vi.fn();
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <ApplicationDialog application={application} onClose={() => {}} onSaved={onSaved} />
    </QueryClientProvider>,
  );
  return onSaved;
}

const problem = (type: string, status = 422) =>
  HttpResponse.json({ type: `/problems/${type}`, title: "Rejected", status }, { status });

describe("ApplicationDialog", () => {
  it("creates an application, sending the fields left empty as null", async () => {
    // Arrange
    let body: unknown;
    server.use(
      http.post("/api/v1/applications", async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(APPLICATION, { status: 201 });
      }),
    );
    const onSaved = renderDialog();
    const user = userEvent.setup();

    // Act
    await user.click(screen.getByRole("combobox", { name: "Company" }));
    await user.click(await screen.findByRole("option", { name: "Acme" }));
    await user.type(screen.getByLabelText("Role"), "Backend Engineer");
    await user.click(screen.getByRole("button", { name: "Create" }));

    // Assert
    expect(onSaved).toHaveBeenCalled();
    expect(body).toEqual({
      company_id: ACME.id,
      role: "Backend Engineer",
      channel: "portal",
      priority: null,
      url: null,
      notes: null,
      stage: "evaluated",
      occurred_on: null,
    });
  });

  it.each([
    ["an unknown company", problem("unknown-company"), "The company does not exist"],
    [
      "a date in the future",
      problem("invalid-transition-date"),
      "The date cannot be in the future",
    ],
    [
      "an invalid URL",
      HttpResponse.json(
        {
          type: "/problems/validation-error",
          title: "Invalid request",
          status: 422,
          errors: [{ field: "body.url", message: "Invalid URL" }],
        },
        { status: 422 },
      ),
      "Invalid URL",
    ],
  ])("shows the error of %s next to its field", async (_, response, message) => {
    // Arrange
    server.use(http.post("/api/v1/applications", () => response));
    const onSaved = renderDialog();
    const user = userEvent.setup();

    // Act
    await user.click(screen.getByRole("button", { name: "Create" }));

    // Assert
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(onSaved).not.toHaveBeenCalled();
  });

  it("edits an application without its stage, sending cleared fields as null", async () => {
    // Arrange
    let body: unknown;
    server.use(
      http.patch(`/api/v1/applications/${APPLICATION.id}`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ ...APPLICATION, notes: null });
      }),
    );
    const onSaved = renderDialog(APPLICATION);
    const user = userEvent.setup();

    // Act
    await user.clear(screen.getByLabelText("Notes"));
    await user.click(screen.getByRole("button", { name: "Save" }));

    // Assert
    expect(onSaved).toHaveBeenCalled();
    expect(screen.queryByLabelText("Start date")).not.toBeInTheDocument();
    expect(body).toEqual({
      company_id: ACME.id,
      role: "Backend Engineer",
      channel: "referral",
      priority: "high",
      url: "https://acme.example/jobs/1",
      notes: null,
    });
  });
});
