import { ThemeProvider } from "@mui/material";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { server } from "../../test/server";
import { theme } from "../../theme";
import { InboxPage } from "./InboxPage";
import type { Offer } from "./OffersGrid";

// specs/ui/inbox.feature, @component scenarios: only an import makes filtered offers, and
// the E2E tests cannot reach the feeds.

const REMOTE_OK_ID = "6f1c1d2e-0000-4000-8000-000000000005";

const offer = (title: string, filtered: boolean): Offer => ({
  id: crypto.randomUUID(),
  url: `https://remoteok.com/${title}`,
  company: "Acme",
  title,
  job_board_id: REMOTE_OK_ID,
  job_board_name: "Remote OK",
  notes: null,
  status: "pending",
  filtered,
  discard_reason: null,
  application_id: null,
  watched_company_id: null,
  watched_company_name: null,
  created_at: "2026-03-10T09:00:00Z",
});

/** One pending offer that fits the profile and one filtered; the API filters them. */
function inboxWithAFilteredOffer() {
  const offers = [offer("Backend Engineer", false), offer("Data Engineer", true)];
  server.use(
    http.get("/api/v1/offers", ({ request }) => {
      const query = new URL(request.url).searchParams;
      const filtered = query.get("filtered");
      const items =
        query.get("status") !== "pending"
          ? []
          : offers.filter((o) => filtered === null || String(o.filtered) === filtered);
      return HttpResponse.json({ items, total: items.length, limit: 20, offset: 0 });
    }),
  );
}

function renderInbox(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter([{ path: "/inbox", element: <InboxPage /> }], {
    initialEntries: [path],
  });
  render(
    <ThemeProvider theme={theme}>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </ThemeProvider>,
  );
}

describe("InboxPage filtered offers", () => {
  it.each([
    ["the filtered view shows only the filtered offers", "/inbox?status=filtered", "Data Engineer"],
    ["the pending view leaves out the filtered offers", "/inbox", "Backend Engineer"],
  ])("%s", async (_name, path, shown) => {
    // Arrange
    inboxWithAFilteredOffer();

    // Act
    renderInbox(path);

    // Assert
    expect(await screen.findByText(shown)).toBeInTheDocument();
    expect(await screen.findByText("1 offer")).toBeInTheDocument();
  });
});
