import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { server } from "../../test/server";
import { ImportJobBoardDialog } from "./ImportJobBoardDialog";

// specs/ui/inbox.feature, @component scenarios: the E2E tests cannot reach the public feeds.

const FIVE_HOURS = 5 * 60 * 60;
const REMOTE_OK_ID = "6f1c1d2e-0000-4000-8000-000000000005";
const IMPORTS_URL = `/api/v1/job-boards/${REMOTE_OK_ID}/imports`;

const jobBoard = (id: string, name: string, feed: string | null) => ({
  id,
  name,
  search_url_template: "https://jobs.example/?q={query}",
  syntax: "keywords",
  import_method: feed ? "api" : "none",
  feed,
  last_imported_at: null,
  next_import_at: null,
});

function jobBoards() {
  const items = [
    jobBoard("6f1c1d2e-0000-4000-8000-000000000004", "LinkedIn", null),
    jobBoard(REMOTE_OK_ID, "Remote OK", "remoteok"),
  ];
  server.use(
    http.get("/api/v1/job-boards", () =>
      HttpResponse.json({ items, total: items.length, limit: 100, offset: 0 }),
    ),
  );
}

function renderDialog() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <ImportJobBoardDialog open onClose={() => {}} />
    </QueryClientProvider>,
  );
}

async function importJobBoard(name: string) {
  const user = userEvent.setup();
  await user.click(screen.getByRole("combobox", { name: "Job board" }));
  await user.click(await screen.findByRole("option", { name }));
  await user.click(screen.getByRole("button", { name: "Import" }));
}

describe("ImportJobBoardDialog", () => {
  it("shows the summary of the import", async () => {
    // Arrange
    jobBoards();
    server.use(
      http.post(IMPORTS_URL, () =>
        HttpResponse.json(
          {
            job_board_id: REMOTE_OK_ID,
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
    await importJobBoard("Remote OK");

    // Assert
    expect(
      await screen.findByText(/1 found, 1 added, 0 filtered, 0 already in the inbox/),
    ).toBeInTheDocument();
  });

  it("says when a job board imported too recently can be imported again", async () => {
    // Arrange
    jobBoards();
    server.use(
      http.post(IMPORTS_URL, () =>
        HttpResponse.json(
          {
            type: "/problems/feed-cooldown",
            title: "Feed imported too recently",
            status: 429,
            detail: "remoteok can be imported again at 2026-03-10T10:00:00+00:00",
          },
          { status: 429, headers: { "Retry-After": String(FIVE_HOURS) } },
        ),
      ),
    );
    renderDialog();

    // Act
    await importJobBoard("Remote OK");

    // Assert
    expect(
      await screen.findByText("Remote OK can be imported again in 5 hours"),
    ).toBeInTheDocument();
  });

  it("offers only the job boards with an import method", async () => {
    // Arrange
    jobBoards();
    renderDialog();
    const user = userEvent.setup();

    // Act
    await user.click(screen.getByRole("combobox", { name: "Job board" }));

    // Assert
    const options = await screen.findAllByRole("option");
    expect(options.map((option) => option.textContent)).toEqual(["Remote OK"]);
  });
});
