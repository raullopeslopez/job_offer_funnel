import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { server } from "../../test/server";
import { ImportWatchedCompanyDialog } from "./ImportWatchedCompanyDialog";
import type { WatchedCompany } from "./WatchedCompaniesPage";

// specs/ui/watched_companies.feature, @component scenarios: the E2E tests cannot reach the ATS.

const PROFILE_ID = "6f1c1d2e-0000-4000-8000-000000000001";
const COMPANY: WatchedCompany = {
  id: "6f1c1d2e-0000-4000-8000-000000000004",
  name: "Acme",
  ats: "greenhouse",
  board: "acme",
  created_at: "2026-03-10T09:00:00Z",
};
const IMPORT_URL = `/api/v1/watched-companies/${COMPANY.id}/imports`;

function profiles() {
  server.use(
    http.get("/api/v1/search-profiles", () =>
      HttpResponse.json({
        items: [
          {
            id: PROFILE_ID,
            name: "Backend",
            titles: ["Backend Engineer"],
            keywords: [],
            excluded_keywords: [],
            location: null,
            work_modes: [],
          },
        ],
        total: 1,
        limit: 100,
        offset: 0,
      }),
    ),
  );
}

function renderDialog() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <ImportWatchedCompanyDialog company={COMPANY} onClose={() => {}} />
    </QueryClientProvider>,
  );
}

async function importFor(profile: string | null) {
  const user = userEvent.setup();
  if (profile) {
    await user.click(screen.getByRole("combobox", { name: "Search profile" }));
    await user.click(await screen.findByRole("option", { name: profile }));
  }
  await user.click(screen.getByRole("button", { name: "Import" }));
}

describe("ImportWatchedCompanyDialog", () => {
  it("shows the summary of the import", async () => {
    // Arrange
    profiles();
    let body: unknown;
    server.use(
      http.post(IMPORT_URL, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(
          {
            imported_at: "2026-03-10T09:00:00Z",
            found: 1,
            matching: 1,
            added: 1,
            already_in_inbox: 0,
            expired: 0,
          },
          { status: 201 },
        );
      }),
    );
    renderDialog();

    // Act
    await importFor("Backend");

    // Assert
    expect(
      await screen.findByText("1 found, 1 matching, 1 added, 0 already in the inbox, 0 expired"),
    ).toBeInTheDocument();
    expect(body).toEqual({ profile_id: PROFILE_ID });
  });

  it("says when the board is not available", async () => {
    // Arrange
    profiles();
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
    await importFor("Backend");

    // Assert
    expect(await screen.findByText(/Board not available/)).toBeInTheDocument();
  });

  it("needs a search profile", async () => {
    // Arrange
    profiles();
    renderDialog();

    // Act
    await importFor(null);

    // Assert
    expect(await screen.findByText("Choose a search profile")).toBeInTheDocument();
  });
});
