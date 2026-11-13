import { ThemeProvider } from "@mui/material";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import type { components } from "../../api/schema";
import { server } from "../../test/server";
import { theme } from "../../theme";
import { InboxPage } from "./InboxPage";
import type { Offer } from "./types";

// specs/ui/inbox.feature, @component scenarios: only an import makes filtered offers, only
// the external reader makes readings, and the E2E tests add every offer today.

const REMOTE_OK_ID = "6f1c1d2e-0000-4000-8000-000000000005";
const DAY_MS = 86_400_000;

type Reading = components["schemas"]["ReadingRead"];

const offer = (title: string, fields: Partial<Offer> = {}): Offer => ({
  id: crypto.randomUUID(),
  url: `https://remoteok.com/${title}`,
  company: "Acme",
  title,
  job_board_id: REMOTE_OK_ID,
  job_board_name: "Remote OK",
  notes: null,
  status: "pending",
  filtered: false,
  readings: [],
  discard_reason: null,
  application_id: null,
  watched_company_id: null,
  watched_company_name: null,
  created_at: new Date().toISOString(),
  ...fields,
});

const reading = (fields: Partial<Reading>): Reading => ({
  admits_location: null,
  admits_location_evidence: null,
  location: null,
  stable: null,
  stable_evidence: null,
  work_mode: null,
  work_mode_evidence: null,
  ...fields,
});

/** The inbox API with these offers; it filters them by status and by `filtered`. */
function inboxWith(offers: Offer[]) {
  server.use(
    http.get("/api/v1/offers", ({ request }) => {
      const query = new URL(request.url).searchParams;
      const filtered = query.get("filtered");
      const items = offers.filter(
        (o) =>
          o.status === query.get("status") &&
          (filtered === null || String(o.filtered) === filtered),
      );
      return HttpResponse.json({ items, total: items.length, limit: 20, offset: 0 });
    }),
    http.get("/api/v1/job-boards", () =>
      HttpResponse.json({ items: [], total: 0, limit: 100, offset: 0 }),
    ),
  );
}

function renderInbox(path = "/inbox") {
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
    [
      "the filtered view shows only the filtered offers",
      "/inbox?status=filtered",
      "Data Engineer",
      "1 filtered",
    ],
    [
      "the pending view leaves out the filtered offers",
      "/inbox",
      "Backend Engineer",
      "1 to decide",
    ],
  ])("%s", async (_name, path, shown, heading) => {
    // Arrange
    inboxWith([offer("Backend Engineer"), offer("Data Engineer", { filtered: true })]);

    // Act
    renderInbox(path);

    // Assert
    expect(await screen.findByRole("heading", { name: heading, level: 1 })).toBeInTheDocument();
    expect(screen.getByRole("article", { name: shown })).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(1);
  });
});

describe("InboxPage groups", () => {
  it("groups the offers by the day they were added", async () => {
    // Arrange
    const now = Date.now();
    inboxWith([
      offer("New one", { created_at: new Date(now).toISOString() }),
      offer("Recent one", { created_at: new Date(now - DAY_MS).toISOString() }),
      offer("Old one", { created_at: new Date(now - 7 * DAY_MS).toISOString() }),
    ]);

    // Act
    renderInbox();

    // Assert
    await screen.findByRole("article", { name: "New one" });
    const groups = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(groups).toEqual(["Today · 1 offer", "Yesterday · 1 offer", "Earlier · 1 offer"]);
  });
});

describe("InboxPage reading strip", () => {
  it.each([
    ["remote", "Remote"],
    ["hybrid", "Hybrid"],
    [null, "Not stated"],
  ] as const)("a reading with the mode %s shows %s", async (mode, shown) => {
    // Arrange
    inboxWith([offer("Backend Engineer", { readings: [reading({ work_mode: mode })] })]);

    // Act
    renderInbox();

    // Assert
    const piece = await screen.findByRole("article", { name: "Backend Engineer" });
    const modeCell = within(piece).getByText("Mode").parentElement as HTMLElement;
    expect(modeCell).toHaveTextContent(shown);
  });

  it.each([
    [{ admits_location: true, location: "Spain" }, "Spain"],
    [{ admits_location: false, location: "Spain" }, "Not from Spain"],
    [{ stable: true }, "Stable"],
    [{ stable: false }, "Not stable"],
  ])("a reading %o shows %s", async (fields, shown) => {
    // Arrange
    inboxWith([offer("Backend Engineer", { readings: [reading(fields)] })]);

    // Act
    renderInbox();

    // Assert
    const piece = await screen.findByRole("article", { name: "Backend Engineer" });
    expect(within(piece).getByText(shown)).toBeInTheDocument();
  });
});
