import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { server } from "../../test/server";
import { ImportFeedDialog } from "./ImportFeedDialog";

// specs/ui/inbox.feature, @component scenarios: the E2E tests cannot reach the public feeds.

const FIVE_HOURS = 5 * 60 * 60;

function feeds() {
  server.use(
    http.get("/api/v1/feeds", () =>
      HttpResponse.json([{ feed: "remoteok", last_imported_at: null, next_import_at: null }]),
    ),
  );
}

function renderDialog() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <ImportFeedDialog open onClose={() => {}} />
    </QueryClientProvider>,
  );
}

async function importFeed(feed: string) {
  const user = userEvent.setup();
  await user.click(screen.getByRole("combobox", { name: "Feed" }));
  await user.click(await screen.findByRole("option", { name: feed }));
  await user.click(screen.getByRole("button", { name: "Import" }));
}

describe("ImportFeedDialog", () => {
  it("shows the summary of the import", async () => {
    // Arrange
    feeds();
    server.use(
      http.post("/api/v1/feeds/remoteok/imports", () =>
        HttpResponse.json(
          {
            feed: "remoteok",
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
    await importFeed("remoteok");

    // Assert
    expect(
      await screen.findByText(/1 found, 1 added, 0 filtered, 0 already in the inbox/),
    ).toBeInTheDocument();
  });

  it("says when a feed imported too recently can be imported again", async () => {
    // Arrange
    feeds();
    server.use(
      http.post("/api/v1/feeds/remoteok/imports", () =>
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
    await importFeed("remoteok");

    // Assert
    expect(
      await screen.findByText("remoteok can be imported again in 5 hours"),
    ).toBeInTheDocument();
  });
});
