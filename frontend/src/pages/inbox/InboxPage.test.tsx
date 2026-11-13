import { ThemeProvider } from "@mui/material";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import type { components } from "../../api/schema";
import { server } from "../../test/server";
import { theme } from "../../theme";
import { InboxPage } from "./InboxPage";
import type { Offer } from "./types";

// specs/ui/inbox.feature, @component scenarios: only an import makes filtered offers and
// filter reasons, only the external reader makes readings, and the E2E tests add every
// offer today.

const REMOTE_OK_ID = "6f1c1d2e-0000-4000-8000-000000000005";
const LINKEDIN_ID = "6f1c1d2e-0000-4000-8000-000000000006";
const PROFILE_ID = "6f1c1d2e-0000-4000-8000-000000000007";
const DAY_MS = 86_400_000;

type Reading = components["schemas"]["ReadingRead"];
type RuleRead = components["schemas"]["RuleRead"];
type Rule = components["schemas"]["Rule"];
type RuleResult = components["schemas"]["RuleResult"];
type SearchProfile = components["schemas"]["SearchProfileRead"];
type JobBoard = components["schemas"]["JobBoardRead"];

const BACKEND: SearchProfile = {
  id: PROFILE_ID,
  name: "Backend",
  titles: ["Backend Engineer"],
  keywords: ["Python", "Django"],
  excluded_keywords: ["Senior"],
  location: "Spain",
  work_modes: ["remote"],
};

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
  filter_reason: null,
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

const rule = (name: Rule, result: RuleResult, fields: Partial<RuleRead> = {}): RuleRead => ({
  rule: name,
  result,
  found: [],
  missing: [],
  value: null,
  evidence: null,
  ...fields,
});

const TITLE_PASSES = rule("title", "passed", { found: ["Backend Engineer"] });

/** The rules of BACKEND that an offer passes, with these ones replaced. */
function rulesWith(...replaced: RuleRead[]): RuleRead[] {
  const passing = [
    TITLE_PASSES,
    rule("keywords", "passed", { found: ["Python", "Django"] }),
    rule("excluded", "passed"),
    rule("work_mode", "passed", { value: "remote" }),
    rule("location", "passed", { value: true }),
    rule("stable", "passed", { value: true }),
  ];
  return passing.map((r) => replaced.find((x) => x.rule === r.rule) ?? r);
}

/** An imported pending offer with its filter reason against BACKEND. */
function imported(
  title: string,
  rules: RuleRead[],
  { hasDescription = true, ...fields }: Partial<Offer> & { hasDescription?: boolean } = {},
): Offer {
  const failed = rules.filter((r) => r.result === "failed");
  const titlePasses = rules.find((r) => r.rule === "title")?.result === "passed";
  return offer(title, {
    filtered: failed.length > 0,
    filter_reason: {
      search_profile_id: PROFILE_ID,
      search_profile_name: "Backend",
      has_description: hasDescription,
      near_miss: titlePasses && failed.length === 1,
      rules,
    },
    ...fields,
  });
}

const nearMiss = (title: string, failing: RuleRead, fields: Partial<Offer> = {}) =>
  imported(title, rulesWith(failing), fields);

const twoRulesAway = () =>
  imported(
    "Senior Backend Engineer",
    rulesWith(
      rule("excluded", "failed", { found: ["Senior"] }),
      rule("stable", "failed", { value: false }),
    ),
  );

const jobBoard = (id: string, name: string, method: JobBoard["import_method"]) =>
  ({ id, name, import_method: method }) as JobBoard;

const isFailing = (o: Offer, name: string) =>
  o.filter_reason?.rules.some((r) => r.rule === name && r.result === "failed") ?? false;

/** The inbox API with these offers; it filters them as the real one does. */
function inboxWith(offers: Offer[], profiles = [BACKEND], jobBoards: JobBoard[] = []) {
  server.use(
    http.get("/api/v1/offers", ({ request }) => {
      const query = new URL(request.url).searchParams;
      const filtered = query.get("filtered");
      const nearMissOnly = query.get("near_miss");
      const failedRule = query.get("failed_rule");
      const limit = Number(query.get("limit") ?? 20);
      const items = offers.filter(
        (o) =>
          o.status === query.get("status") &&
          (filtered === null || String(o.filtered) === filtered) &&
          (nearMissOnly === null || String(o.filter_reason?.near_miss ?? false) === nearMissOnly) &&
          (failedRule === null || isFailing(o, failedRule)),
      );
      return HttpResponse.json({
        items: items.slice(0, limit),
        total: items.length,
        limit,
        offset: 0,
      });
    }),
    http.get("/api/v1/offers/filtered-counts", () => {
      const filtered = offers.filter((o) => o.status === "pending" && o.filtered);
      const rules: Rule[] = ["title", "keywords", "excluded", "work_mode", "location", "stable"];
      return HttpResponse.json({
        filtered: filtered.length,
        near_misses: filtered.filter((o) => o.filter_reason?.near_miss).length,
        failing: Object.fromEntries(
          rules.map((name) => [name, filtered.filter((o) => isFailing(o, name)).length]),
        ),
      });
    }),
    http.get("/api/v1/job-boards", () =>
      HttpResponse.json({ items: jobBoards, total: jobBoards.length, limit: 100, offset: 0 }),
    ),
    http.get("/api/v1/search-profiles", () =>
      HttpResponse.json({ items: profiles, total: profiles.length, limit: 100, offset: 0 }),
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

/** The cell of a rule in a piece, failed or not. */
function cellOf(piece: HTMLElement, label: string): HTMLElement {
  const name = within(piece).getByText(new RegExp(`^${label}( · filtered it)?$`));
  return name.parentElement as HTMLElement;
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
    inboxWith([
      offer("Backend Engineer"),
      imported("Data Engineer", rulesWith(rule("title", "failed"))),
    ]);

    // Act
    renderInbox(path);

    // Assert
    expect(await screen.findByRole("heading", { name: heading, level: 1 })).toBeInTheDocument();
    expect(await screen.findByRole("article", { name: shown })).toBeInTheDocument();
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
    inboxWith([
      offer("Backend Engineer", { status: "discarded", readings: [reading({ work_mode: mode })] }),
    ]);

    // Act
    renderInbox("/inbox?status=discarded");

    // Assert
    const piece = await screen.findByRole("article", { name: "Backend Engineer" });
    expect(cellOf(piece, "Mode")).toHaveTextContent(shown);
  });

  it.each([
    [{ admits_location: true, location: "Spain" }, "Spain"],
    [{ admits_location: false, location: "Spain" }, "Not from Spain"],
    [{ stable: true }, "Stable"],
    [{ stable: false }, "Not stable"],
  ])("a reading %o shows %s", async (fields, shown) => {
    // Arrange
    inboxWith([offer("Backend Engineer", { status: "discarded", readings: [reading(fields)] })]);

    // Act
    renderInbox("/inbox?status=discarded");

    // Assert
    const piece = await screen.findByRole("article", { name: "Backend Engineer" });
    expect(within(piece).getByText(shown)).toBeInTheDocument();
  });
});

describe("InboxPage rule strip", () => {
  it.each([
    [TITLE_PASSES, "Title", "Backend Engineer", "pass"],
    [
      rule("keywords", "passed", { found: ["Python", "Django"] }),
      "Keywords",
      "Python, Django",
      "pass",
    ],
    [rule("work_mode", "passed", { value: "remote" }), "Mode", "Remote", "pass"],
    [rule("work_mode", "unknown"), "Mode", "Not stated", "unknown"],
    [rule("location", "passed", { value: true }), "Location", "Spain", "pass"],
    [rule("stable", "passed", { value: true }), "Contract", "Stable", "pass"],
    [rule("stable", "unknown"), "Contract", "Not stated", "unknown"],
  ])("a %o rule shows in %s as %s", async (given, label, shown, state) => {
    // Arrange
    inboxWith([imported("Backend Engineer", rulesWith(given))]);

    // Act
    renderInbox();

    // Assert
    const piece = await screen.findByRole("article", { name: "Backend Engineer" });
    const cell = cellOf(piece, label);
    expect(cell).toHaveTextContent(shown);
    expect(cell).toHaveAttribute("data-state", state);
  });

  it('a rule the profile does not ask for says "Any"', async () => {
    // Arrange
    const titleOnly = {
      ...BACKEND,
      keywords: [],
      excluded_keywords: [],
      location: null,
      work_modes: [],
    };
    inboxWith(
      [imported("Backend Engineer", [TITLE_PASSES, rule("stable", "passed", { value: true })])],
      [titleOnly],
    );

    // Act
    renderInbox();

    // Assert
    const piece = await screen.findByRole("article", { name: "Backend Engineer" });
    for (const label of ["Keywords", "Mode", "Location"]) {
      expect(cellOf(piece, label)).toHaveTextContent("Any");
    }
  });

  it.each([
    [
      LINKEDIN_ID,
      "Mode, location and contract unknown: email alerts arrive without a description to read",
    ],
    [REMOTE_OK_ID, "Mode, location and contract unknown: the offer has no description to read"],
  ])("an offer of %s without a description merges its reading rules", async (boardId, merged) => {
    // Arrange
    inboxWith(
      [
        imported("Backend Engineer", [TITLE_PASSES, rule("stable", "unknown")], {
          hasDescription: false,
          job_board_id: boardId,
        }),
      ],
      [BACKEND],
      [jobBoard(REMOTE_OK_ID, "Remote OK", "api"), jobBoard(LINKEDIN_ID, "LinkedIn", "email")],
    );

    // Act
    renderInbox();

    // Assert
    const piece = await screen.findByRole("article", { name: "Backend Engineer" });
    expect(cellOf(piece, "Title")).toHaveTextContent("Backend Engineer");
    expect(within(piece).getByText(merged)).toBeInTheDocument();
  });

  it("an offer added by hand says it has nothing to read", async () => {
    // Arrange
    inboxWith([offer("Backend Engineer", { job_board_id: null, job_board_name: null })]);

    // Act
    renderInbox();

    // Assert
    const piece = await screen.findByRole("article", { name: "Backend Engineer" });
    expect(
      within(piece).getByText("Mode, location and contract unknown: you added it by hand"),
    ).toBeInTheDocument();
  });
});

describe("InboxPage failed cells", () => {
  it.each([
    [
      "Senior Backend Engineer",
      rule("excluded", "failed", { found: ["Senior"] }),
      "Title",
      '"Senior", you exclude it',
    ],
    [
      "Backend Engineer",
      rule("keywords", "failed", { found: ["Python"], missing: ["Django"] }),
      "Keywords",
      "Missing: Django",
    ],
    [
      "Backend Engineer",
      rule("work_mode", "failed", { value: "hybrid", evidence: "Two days in the office" }),
      "Mode",
      "Hybrid, you ask Remote",
    ],
    [
      "Backend Engineer",
      rule("location", "failed", { value: false, evidence: "Only residents of the US" }),
      "Location",
      "Not from Spain",
    ],
    [
      "Backend Engineer",
      rule("stable", "failed", { value: false, evidence: "A six-month contract" }),
      "Contract",
      "Not stable",
    ],
    ["Data Engineer", rule("title", "failed"), "Title", "No title of yours"],
  ])("%s failing %o shows in %s %s", async (title, failing, label, shown) => {
    // Arrange
    const user = userEvent.setup();
    inboxWith([nearMiss(title, failing)]);
    renderInbox("/inbox?status=filtered");
    await screen.findByRole("heading", { name: "1 filtered", level: 1 });

    // Act
    if (failing.rule !== "title") {
      await user.click(await screen.findByRole("button", { name: "Show" }));
    }

    // Assert
    const piece = await screen.findByRole("article", { name: title });
    const cell = cellOf(piece, label);
    expect(cell).toHaveTextContent(`${label} · filtered it`);
    expect(cell).toHaveTextContent(shown);
    expect(cell).toHaveAttribute("data-state", "failed");
    if (failing.evidence) {
      expect(within(piece).getByText(`“${failing.evidence}”`)).toBeInTheDocument();
    }
  });
});

describe("InboxPage maybe", () => {
  const fiveNearMisses = () =>
    [1, 2, 3, 4, 5].map((n) =>
      nearMiss(`Backend Engineer ${n}`, rule("stable", "failed", { value: false }), {
        created_at: new Date(Date.now() - n * 60_000).toISOString(),
      }),
    );

  it("closes the pending view with the three most recent near misses", async () => {
    // Arrange
    inboxWith([offer("Pending one"), ...fiveNearMisses(), twoRulesAway()]);

    // Act
    renderInbox();

    // Assert
    const maybe = await screen.findByRole("region", { name: "Maybe" });
    const groups = screen.getAllByRole("heading", { level: 2 });
    expect(groups.at(-1)).toHaveTextContent("Maybe · 3 of 5 near misses");
    expect(
      within(maybe).getByText(
        "Filtered by a single rule. Promoting one tells the app the rule was too strict.",
      ),
    ).toBeInTheDocument();
    const pieces = within(maybe).getAllByRole("article");
    expect(pieces.map((p) => p.getAttribute("aria-label"))).toEqual([
      "Backend Engineer 1",
      "Backend Engineer 2",
      "Backend Engineer 3",
    ]);
    for (const piece of pieces) {
      expect(cellOf(piece, "Contract")).toHaveAttribute("data-state", "failed");
      expect(within(piece).getByRole("button", { name: "Promote anyway" })).toBeInTheDocument();
    }
  });

  it('without near misses there is no "Maybe"', async () => {
    // Arrange
    inboxWith([offer("Pending one"), twoRulesAway()]);

    // Act
    renderInbox();

    // Assert
    await screen.findByRole("article", { name: "Pending one" });
    expect(screen.queryByRole("region", { name: "Maybe" })).not.toBeInTheDocument();
  });

  it("promotes a near miss anyway", async () => {
    // Arrange
    const user = userEvent.setup();
    const candidate = nearMiss("Backend Engineer", rule("stable", "failed", { value: false }));
    inboxWith([candidate]);
    let promoted: unknown = null;
    server.use(
      http.post("/api/v1/offers/:offerId/promotion", async ({ params, request }) => {
        promoted = { offerId: params.offerId, ...((await request.json()) as object) };
        return HttpResponse.json({}, { status: 201 });
      }),
    );
    renderInbox();
    const maybe = await screen.findByRole("region", { name: "Maybe" });

    // Act
    await user.click(within(maybe).getByRole("button", { name: "Promote anyway" }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Promote" }));

    // Assert
    expect(await screen.findByText("Application created")).toBeInTheDocument();
    expect(promoted).toEqual({ offerId: candidate.id, channel: "portal" });
  });
});

describe("InboxPage filtered by rule", () => {
  it("groups the near misses by the rule that filtered them", async () => {
    // Arrange
    const excluded = (word: string) => rule("excluded", "failed", { found: [word] });
    inboxWith([
      nearMiss("Junior Backend Engineer", excluded("Junior")),
      nearMiss("Junior Python Developer", excluded("Junior")),
      nearMiss("Backend Intern", excluded("Intern")),
      nearMiss("Backend Engineer", rule("work_mode", "failed", { value: "hybrid" })),
      twoRulesAway(),
    ]);

    // Act
    renderInbox("/inbox?status=filtered");

    // Assert
    const away = await screen.findByRole("region", { name: "One rule away" });
    expect(within(away).getByRole("heading", { level: 2 })).toHaveTextContent(
      "One rule away · 4 offers",
    );
    await within(away).findByText("Junior 2 · Intern 1");
    const groups = within(away).getAllByRole("region");
    expect(groups.map((g) => g.getAttribute("aria-label"))).toEqual(["A word you exclude", "Mode"]);
    expect(groups[0]).toHaveTextContent("3");
    expect(groups[0]).toHaveTextContent("Junior 2 · Intern 1");
    expect(groups[1]).toHaveTextContent("1");
    expect(groups[1]).toHaveTextContent("Hybrid 1");
    expect(screen.getByRole("heading", { name: "Further away · 1 offer" })).toBeInTheDocument();
  });

  it("opens a group of near misses to show its offers", async () => {
    // Arrange
    const user = userEvent.setup();
    inboxWith([
      nearMiss("Junior Backend Engineer", rule("excluded", "failed", { found: ["Junior"] })),
    ]);
    renderInbox("/inbox?status=filtered");
    const group = await screen.findByRole("region", { name: "A word you exclude" });
    expect(within(group).queryByRole("article")).not.toBeInTheDocument();

    // Act
    await user.click(within(group).getByRole("button", { name: "Show" }));

    // Assert
    const row = await within(group).findByRole("article", { name: "Junior Backend Engineer" });
    expect(row).toHaveTextContent("Remote OK");
    expect(row).toHaveTextContent("Acme");
    expect(cellOf(row, "Title")).toHaveAttribute("data-state", "failed");
    expect(within(row).getByRole("button", { name: "Promote anyway" })).toBeInTheDocument();
  });

  it("lists the offers further away with their strip", async () => {
    // Arrange
    inboxWith([
      imported("Data Engineer", rulesWith(rule("title", "failed")), { company: "Globex" }),
      nearMiss("Junior Backend Engineer", rule("excluded", "failed", { found: ["Junior"] })),
    ]);

    // Act
    renderInbox("/inbox?status=filtered");

    // Assert
    const further = await screen.findByRole("region", { name: "Further away" });
    const pieces = await within(further).findAllByRole("article");
    expect(pieces.map((p) => p.getAttribute("aria-label"))).toEqual(["Data Engineer"]);
    const title = cellOf(pieces[0] as HTMLElement, "Title");
    expect(title).toHaveTextContent("No title of yours");
    expect(title).toHaveAttribute("data-state", "failed");
  });
});
