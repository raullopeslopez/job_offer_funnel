import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { server } from "../../test/server";
import { ImportFeedDialog } from "./ImportFeedDialog";

// specs/ui/inbox.feature, @component scenarios: the E2E tests cannot reach the public feeds.

const PROFILE_ID = "6f1c1d2e-0000-4000-8000-000000000001";
const FIVE_HOURS = 5 * 60 * 60;

function feedsAndProfiles() {
  server.use(
    http.get("/api/v1/feeds", () =>
      HttpResponse.json([{ feed: "remoteok", last_imported_at: null, next_import_at: null }]),
    ),
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
      <ImportFeedDialog open onClose={() => {}} />
    </QueryClientProvider>,
  );
}

async function importFeed(feed: string, profile: string) {
  const user = userEvent.setup();
  await user.click(screen.getByRole("combobox", { name: "Feed" }));
  await user.click(await screen.findByRole("option", { name: feed }));
  await user.click(screen.getByRole("combobox", { name: "Search profile" }));
  await user.click(await screen.findByRole("option", { name: profile }));
  await user.click(screen.getByRole("button", { name: "Import" }));
}

describe("ImportFeedDialog", () => {
  it("shows the summary of the import", async () => {
    // Arrange
    feedsAndProfiles();
    let body: unknown;
    server.use(
      http.post("/api/v1/feeds/remoteok/imports", async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(
          {
            feed: "remoteok",
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
    await importFeed("remoteok", "Backend");

    // Assert
    expect(
      await screen.findByText(/1 found, 1 matching, 1 added, 0 already in the inbox/),
    ).toBeInTheDocument();
    expect(body).toEqual({ profile_id: PROFILE_ID });
  });

  it("says when a feed imported too recently can be imported again", async () => {
    // Arrange
    feedsAndProfiles();
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
    await importFeed("remoteok", "Backend");

    // Assert
    expect(
      await screen.findByText("remoteok can be imported again in 5 hours"),
    ).toBeInTheDocument();
  });
});
