import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { server } from "../../test/server";
import type { WatchedCompany } from "../sources/types";
import { ImportWatchedCompanyDialog } from "./ImportWatchedCompanyDialog";

// specs/ui/sources.feature, @component scenarios of the watched companies: the E2E tests cannot reach the ATS.

const COMPANY: WatchedCompany = {
  id: "6f1c1d2e-0000-4000-8000-000000000004",
  name: "Acme",
  ats: "greenhouse",
  board: "acme",
  created_at: "2026-03-10T09:00:00Z",
};
const IMPORT_URL = `/api/v1/watched-companies/${COMPANY.id}/imports`;

function renderDialog() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <ImportWatchedCompanyDialog company={COMPANY} onClose={() => {}} />
    </QueryClientProvider>,
  );
}

async function importCompany() {
  await userEvent.setup().click(screen.getByRole("button", { name: "Import" }));
}

describe("ImportWatchedCompanyDialog", () => {
  it("shows the summary of the import", async () => {
    // Arrange
    server.use(
      http.post(IMPORT_URL, () =>
        HttpResponse.json(
          {
            watched_company_id: COMPANY.id,
            imported_at: "2026-03-10T09:00:00Z",
            found: 1,
            added: 1,
            filtered: 0,
            already_in_inbox: 0,
            expired: 0,
          },
          { status: 201 },
        ),
      ),
    );
    renderDialog();

    // Act
    await importCompany();

    // Assert
    expect(
      await screen.findByText("1 found, 1 added, 0 filtered, 0 already in the inbox, 0 expired"),
    ).toBeInTheDocument();
  });

  it("says when the board is not available", async () => {
    // Arrange
    server.use(
      http.post(IMPORT_URL, () =>
        HttpResponse.json(
          { type: "/problems/board-unavailable", title: "Board not available", status: 502 },
          { status: 502 },
        ),
      ),
    );
    renderDialog();

    // Act
    await importCompany();

    // Assert
    expect(await screen.findByText(/Board not available/)).toBeInTheDocument();
  });
});
