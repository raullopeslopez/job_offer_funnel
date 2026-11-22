import { ThemeProvider } from "@mui/material";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import type { components } from "../../api/schema";
import { server } from "../../test/server";
import { setViewportWidth } from "../../test/viewport";
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

type Triage = NonNullable<Offer["triage"]>;

/** A triage as the specs put it: OK "because" is its why yes, KO "because" its why not. */
const triaged = (verdict: "ok" | "ko", why: string, fields: Partial<Triage> = {}): Triage => ({
  verdict,
  why_yes: verdict === "ok" ? { why, quote: null } : null,
  why_not: verdict === "ko" ? { why, quote: null } : null,
  confidence: null,
  ...fields,
});

const offer = (title: string, fields: Partial<Offer> = {}): Offer => ({
  id: crypto.randomUUID(),
  url: `https://remoteok.com/${title}`,
  company: "Acme",
  title,
  job_board_id: REMOTE_OK_ID,
  job_board_name: "Remote OK",
  location: null,
  countries: [],
  base_title: title,
  variants: 1,
  notes: null,
  status: "pending",
  filtered: false,
  filter_reason: null,
  readings: [],
  discard_reason: null,
  discard_word: null,
  triager_discard: null,
  application_id: null,
  review: null,
  review_rules: [],
  triage: null,
  suggested_discard: null,
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
  engineering: null,
  engineering_evidence: null,
  stack: [],
  stack_evidence: null,
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
    rule("engineering", "passed", { value: true }),
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
function noCriteriaSuggestions() {
  server.use(
    http.get("/api/v1/criteria-suggestions", () =>
      HttpResponse.json({ items: [], total: 0, limit: 100, offset: 0 }),
    ),
  );
}

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
    http.get("/api/v1/offers/near-misses", ({ request }) => {
      const limit = Number(new URL(request.url).searchParams.get("limit") ?? 20);
      const nearMisses = offers.filter((o) => o.status === "pending" && o.filter_reason?.near_miss);
      const rules: Rule[] = [
        "keywords",
        "excluded",
        "work_mode",
        "location",
        "stable",
        "engineering",
      ];
      const groups = rules
        .map((rule) => ({ rule, offers: nearMisses.filter((o) => isFailing(o, rule)) }))
        .filter(({ offers }) => offers.length > 0)
        .map(({ rule, offers }) => ({
          rule,
          total: offers.length,
          offers: offers.slice(0, limit),
        }));
      return HttpResponse.json({ groups });
    }),
    http.get("/api/v1/job-boards", () =>
      HttpResponse.json({ items: jobBoards, total: jobBoards.length, limit: 100, offset: 0 }),
    ),
    http.get("/api/v1/search-profiles", () =>
      HttpResponse.json({ items: profiles, total: profiles.length, limit: 100, offset: 0 }),
    ),
    http.get("/api/v1/offers/frequent-titles", () => HttpResponse.json({ offers: 0, titles: [] })),
    // Without an offer triager, as the E2E tests; the triage tests make one available.
    http.get("/api/v1/offers/triager", () =>
      HttpResponse.json({ is_available: false, discardable: 0 }),
    ),
  );
}

/**
 * "The inbox is slow to list the offers again": once an offer is discarded, listing the
 * offers waits until `release` is called. Returns `release`, for the end of the test.
 */
function slowToListAfterDiscard(): () => void {
  let isDiscarded = false;
  let release!: () => void;
  const released = new Promise<void>((resolve) => {
    release = resolve;
  });
  server.use(
    // Falls through to the inbox handlers once released.
    http.get("/api/v1/offers", async () => {
      if (isDiscarded) await released;
    }),
    http.post("/api/v1/offers/:offerId/discard", () => {
      isDiscarded = true;
      return HttpResponse.json({}, { status: 201 });
    }),
  );
  return release;
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

type User = ReturnType<typeof userEvent.setup>;

const offerList = () => screen.getByRole("region", { name: "Offer list" });
const readingPane = () => screen.getByRole("region", { name: "Reading pane" });

/** The titles of the rows, in order: of the whole list, or of one of its groups. */
function rowTitles(scope: HTMLElement = offerList()): string[] {
  return within(scope)
    .getAllByRole("listitem")
    .map((row) => within(row).getByRole("button").textContent ?? "");
}

/** Chooses the row of an offer and returns the offer, as the reading pane shows it. */
async function openRow(user: User, title: string): Promise<HTMLElement> {
  await user.click(await within(offerList()).findByRole("button", { name: title }));
  return openedPane(title);
}

/** The reading pane once it shows an offer: its offer and its action bar. */
async function openedPane(title: string): Promise<HTMLElement> {
  await within(readingPane()).findByRole("article", { name: title });
  return readingPane();
}

/** The cell of a rule in a piece, failed or not. */
function cellOf(piece: HTMLElement, label: string): HTMLElement {
  const name = within(piece).getByText(new RegExp(`^${label}$`));
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
    expect(await screen.findByText(heading)).toBeInTheDocument();
    expect(await screen.findByRole("article", { name: shown })).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(1);
  });
});

// specs/ui/inbox.feature: "An offer shows its first country as a tag and how many more it has".
describe("InboxPage country tags", () => {
  it.each<[string, string[], string, string]>([
    ["Madrid, Spain", ["Spain"], "Spain", ""],
    ["Spain, Portugal", ["Spain", "Portugal"], "Spain", "+1 country"],
    ["Worldwide", ["Worldwide"], "Worldwide", ""],
    ["San Francisco, CA", [], "San Francisco, CA", ""],
  ])("an offer located in %j shows the tag %j and %j", async (location, countries, tag, more) => {
    // Arrange
    inboxWith([imported("Backend Engineer", rulesWith(), { location, countries })]);

    // Act
    renderInbox();

    // Assert
    const piece = await openedPane("Backend Engineer");
    const shown = within(piece)
      .getAllByTitle("Country")
      .map((shownTag) => shownTag.textContent);
    expect(shown).toEqual([tag]);
    if (more) expect(piece).toHaveTextContent(more);
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

  it("shows the variants next to each other as one closed row that opens", async () => {
    // Arrange: specs/ui/inbox.feature, "Variants".
    const user = userEvent.setup();
    const variant = { base_title: "Backend Engineer", variants: 2 };
    inboxWith([
      offer("Backend Engineer - Platform", variant),
      offer("Backend Engineer - Payments", variant),
      offer("Data Engineer"),
    ]);
    renderInbox();
    const first = await openRow(user, "Backend Engineer - Platform");
    const closed = rowTitles();
    const firstRow = within(offerList()).getAllByRole("listitem")[0];

    // Act
    await user.click(
      within(first).getByRole("button", { name: "1 more variant of this role", expanded: false }),
    );

    // Assert
    expect(closed).toEqual(["Backend Engineer - Platform", "Data Engineer"]);
    expect(firstRow).toHaveTextContent("+1 variant");
    expect(rowTitles()).toEqual([
      "Backend Engineer - Platform",
      "Backend Engineer - Payments",
      "Data Engineer",
    ]);
  });

  it("selects the first offer of the view, and the offer of the row chosen", async () => {
    // Arrange: specs/ui/inbox.feature, "Choosing a row opens its offer in the reading pane".
    const user = userEvent.setup();
    inboxWith([offer("C"), offer("B"), offer("A")]);
    renderInbox();
    const first = await within(offerList()).findByRole("button", { name: "C" });
    const opened = within(readingPane()).getByRole("article").getAttribute("aria-label");

    // Act
    await user.click(within(offerList()).getByRole("button", { name: "A" }));

    // Assert
    expect(opened).toBe("C");
    expect(first).not.toHaveAttribute("aria-current");
    expect(within(offerList()).getByRole("button", { name: "A" })).toHaveAttribute(
      "aria-current",
      "true",
    );
    expect(within(readingPane()).getByRole("article", { name: "A" })).toBeInTheDocument();
  });

  it("on a phone no offer is open until a row is tapped, and it opens full screen", async () => {
    // Arrange: specs/ui/inbox.feature, "On a phone".
    const user = userEvent.setup();
    setViewportWidth(390);
    inboxWith([offer("C"), offer("B"), offer("A")]);
    renderInbox();
    await within(offerList()).findByRole("button", { name: "B" });
    const closed = screen.queryByRole("region", { name: "Reading pane" });

    // Act
    await user.click(within(offerList()).getByRole("button", { name: "B" }));
    const pane = readingPane();
    const header = {
      back: within(pane).getByRole("button", { name: "Back" }),
      original: within(pane).getAllByRole("link", { name: "Original posting" }),
      position: within(pane).getByText("2 of 3"),
    };

    // Assert
    expect(closed).toBeNull();
    expect(header.back).toBeInTheDocument();
    expect(header.original).toHaveLength(1);
    expect(header.position).toBeInTheDocument();
    expect(within(pane).getByRole("button", { name: "Discard" })).toBeInTheDocument();
  });

  it("with verdicts, the pending view goes by verdict", async () => {
    // Arrange: the API lists them by verdict when asked to.
    const discard = (reason: "stack" | "contract") => ({ reason, evidence: "Evidence." });
    const byVerdict = [
      offer("Senior Backend Engineer", { triage: triaged("ok", "Fits.") }),
      offer("Backend Engineer"),
      offer("Go Engineer", { triage: triaged("ko", "Go."), suggested_discard: discard("stack") }),
      offer("Part-time Engineer", {
        triage: triaged("ko", "Part-time."),
        suggested_discard: discard("contract"),
      }),
      offer("Python Engineer", { triage: triaged("ko", "Not for you.") }),
    ];
    const asked: (string | null)[] = [];
    inboxWith(byVerdict);
    server.use(
      http.get("/api/v1/offers", ({ request }) => {
        const query = new URL(request.url).searchParams;
        if (query.get("limit") !== "1") asked.push(query.get("by_verdict"));
        const items = query.get("status") === "pending" && query.get("filtered") === "false";
        const listed = items ? byVerdict : [];
        return HttpResponse.json({ items: listed, total: listed.length, limit: 20, offset: 0 });
      }),
    );

    // Act
    renderInbox();

    // Assert
    await within(offerList()).findByRole("button", { name: "Python Engineer" });
    expect(asked).toContain("true");
    const groups = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(groups).toEqual([
      "AI: OK · 1 offer",
      "Not triaged · 1 offer",
      "AI: KO · Stack · 1 offer",
      "AI: KO · Contract · 1 offer",
      "AI: KO · 1 offer",
    ]);
    expect(rowTitles()).toEqual(byVerdict.map((o) => o.title));
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
    const piece = await openedPane("Backend Engineer");
    expect(cellOf(piece, "Mode")).toHaveTextContent(shown);
  });

  it.each([
    [{ admits_location: true, location: "Spain" }, "Spain"],
    [{ admits_location: false, location: "Spain" }, "Not from Spain"],
    [{ stable: true }, "Stable"],
    [{ stable: false }, "Not stable"],
    [{ engineering: true }, "Engineering"],
    [{ engineering: false }, "Not engineering"],
    [{ stack: ["Python", "Django"] }, "Python, Django"],
  ])("a reading %o shows %s", async (fields, shown) => {
    // Arrange
    inboxWith([offer("Backend Engineer", { status: "discarded", readings: [reading(fields)] })]);

    // Act
    renderInbox("/inbox?status=discarded");

    // Assert
    const piece = await openedPane("Backend Engineer");
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
    [rule("engineering", "passed", { value: true }), "Role", "Engineering", "pass"],
  ])("a %o rule shows in %s as %s", async (given, label, shown, state) => {
    // Arrange
    inboxWith([imported("Backend Engineer", rulesWith(given))]);

    // Act
    renderInbox();

    // Assert
    const piece = await openedPane("Backend Engineer");
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
    const piece = await openedPane("Backend Engineer");
    for (const label of ["Keywords", "Mode", "Location"]) {
      expect(cellOf(piece, label)).toHaveTextContent("Any");
    }
  });

  it.each([
    [
      LINKEDIN_ID,
      "Mode, location, contract, role and stack unknown: email alerts arrive without a description to read",
    ],
    [
      REMOTE_OK_ID,
      "Mode, location, contract, role and stack unknown: the offer has no description to read",
    ],
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
    const piece = await openedPane("Backend Engineer");
    expect(cellOf(piece, "Title")).toHaveTextContent("Backend Engineer");
    expect(within(piece).getByText(merged)).toBeInTheDocument();
  });

  it("an offer added by hand says it has nothing to read", async () => {
    // Arrange
    inboxWith([offer("Backend Engineer", { job_board_id: null, job_board_name: null })]);

    // Act
    renderInbox();

    // Assert
    const piece = await openedPane("Backend Engineer");
    expect(
      within(piece).getByText(
        "Mode, location, contract, role and stack unknown: you added it by hand",
      ),
    ).toBeInTheDocument();
  });
});

describe("InboxPage stack cell", () => {
  it.each([
    [["Python", "Django"], "Python, Django", "pass"],
    [[], "Not stated", "unknown"],
  ])("a reading with the stack %o shows %s", async (stack, shown, state) => {
    // Arrange
    inboxWith([
      imported("Backend Engineer", rulesWith(), {
        readings: [reading({ stack, location: "Spain" })],
      }),
    ]);

    // Act
    renderInbox();

    // Assert
    const piece = await openedPane("Backend Engineer");
    const cell = cellOf(piece, "Stack");
    expect(cell).toHaveTextContent(shown);
    expect(cell).toHaveAttribute("data-state", state);
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
    [
      "Backend Engineer",
      rule("engineering", "failed", { value: false, evidence: "Run technical demos" }),
      "Role",
      "Not engineering",
    ],
    [
      "Backend Engineer",
      rule("excluded", "failed", { found: ["Node"], evidence: "Node.js and TypeScript" }),
      "Title",
      '"Node" in its stack, you exclude it',
    ],
    ["Data Engineer", rule("title", "failed"), "Title", "No title of yours"],
  ])("%s failing %o shows in %s %s", async (title, failing, label, shown) => {
    // Arrange
    const user = userEvent.setup();
    inboxWith([nearMiss(title, failing)]);
    renderInbox("/inbox?status=filtered");
    await screen.findByText("1 filtered");

    // Act
    const piece = await openRow(user, title);

    // Assert
    const cell = cellOf(piece, label);
    expect(cell).toHaveTextContent("filtered it");
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
    const user = userEvent.setup();
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
    const titles = rowTitles(maybe);
    expect(titles).toEqual(["Backend Engineer 1", "Backend Engineer 2", "Backend Engineer 3"]);
    for (const title of titles) {
      const piece = await openRow(user, title);
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
    const piece = await openRow(user, "Backend Engineer");

    // Act
    await user.click(within(piece).getByRole("button", { name: "Promote anyway" }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Promote" }));

    // Assert
    expect(await screen.findByText("Application created")).toBeInTheDocument();
    expect(promoted).toEqual({ offerId: candidate.id, channel: "portal" });
  });
});

// specs/ui/inbox.feature: "Mark a near miss as rightly filtered".
describe("InboxPage rightly filtered", () => {
  it.each([
    ["Maybe", "/inbox"],
    ["A word you exclude", "/inbox?status=filtered"],
  ])("marks a near miss in %s as rightly filtered", async (group, path) => {
    // Arrange
    const user = userEvent.setup();
    const candidate = nearMiss(
      "Junior Backend Engineer",
      rule("excluded", "failed", { found: ["Junior"] }),
    );
    inboxWith([candidate]);
    let marked: unknown = null;
    server.use(
      http.post("/api/v1/offers/:offerId/rightly-filtered", ({ params }) => {
        marked = params.offerId;
        if (candidate.filter_reason) candidate.filter_reason.near_miss = false;
        return HttpResponse.json({}, { status: 201 });
      }),
    );
    renderInbox(path);
    await screen.findByRole("region", { name: group });
    const piece = await openRow(user, "Junior Backend Engineer");

    // Act
    await user.click(within(piece).getByRole("button", { name: "Rightly filtered" }));

    // Assert
    expect(await screen.findByText("Marked as rightly filtered")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Undo" })).toBeInTheDocument();
    expect(marked).toBe(candidate.id);
    await waitFor(() =>
      expect(screen.queryByRole("region", { name: group })).not.toBeInTheDocument(),
    );
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

  it("lists the offers of a group of near misses under it, always open", async () => {
    // Arrange
    inboxWith([
      nearMiss("Junior Backend Engineer", rule("excluded", "failed", { found: ["Junior"] })),
    ]);

    // Act
    renderInbox("/inbox?status=filtered");

    // Assert
    const group = await screen.findByRole("region", { name: "A word you exclude" });
    expect(within(group).queryByRole("button", { name: /^(Show|Hide)$/ })).not.toBeInTheDocument();
    const row = await within(group).findByRole("listitem");
    expect(rowTitles(group)).toEqual(["Junior Backend Engineer"]);
    expect(row).toHaveTextContent("Remote OK");
    expect(row).toHaveTextContent("Acme");
    const piece = await openedPane("Junior Backend Engineer");
    expect(cellOf(piece, "Title")).toHaveAttribute("data-state", "failed");
    expect(within(piece).getByRole("button", { name: "Promote anyway" })).toBeInTheDocument();
  });

  it("lists the offers further away with their strip", async () => {
    // Arrange
    inboxWith([
      imported("Data Engineer", rulesWith(rule("title", "failed")), { company: "Globex" }),
      nearMiss("Junior Backend Engineer", rule("excluded", "failed", { found: ["Junior"] })),
    ]);

    const user = userEvent.setup();
    renderInbox("/inbox?status=filtered");

    // Act
    const further = await screen.findByRole("region", { name: "Further away" });
    await openRow(user, "Data Engineer");

    // Assert
    expect(rowTitles(further)).toEqual(["Data Engineer"]);
    const piece = within(readingPane()).getByRole("article", { name: "Data Engineer" });
    const title = cellOf(piece, "Title");
    expect(title).toHaveTextContent("No title of yours");
    expect(title).toHaveAttribute("data-state", "failed");
  });
});

// specs/ui/inbox.feature: "A word in the title of an imported offer proposes excluding it
// from its profile" and "Discard only the offer, or also exclude the word from the profile".
describe("InboxPage exclusion proposal", () => {
  type User = ReturnType<typeof userEvent.setup>;
  type Preview = components["schemas"]["CriteriaPreviewRead"];

  const lead = () => imported("Lead Backend Engineer", rulesWith());

  function previewing(preview: Partial<Preview> = {}) {
    const asked: unknown[] = [];
    server.use(
      http.post("/api/v1/offers/criteria-previews", async ({ request }) => {
        asked.push(await request.json());
        return HttpResponse.json({
          entering_pending: 0,
          leaving_pending: 1,
          promoted_filtered: 0,
          discarded_filtered: 0,
          ...preview,
        });
      }),
    );
    return asked;
  }

  async function chooseWord(user: User, title: string, word: string) {
    const piece = await openedPane(title);
    await user.click(within(piece).getByRole("button", { name: "Discard" }));
    // Discarding opens another piece for the same offer.
    const opened = await openedPane(title);
    const words = within(opened).getByRole("group", { name: "A word in the title" });
    await user.click(within(words).getByRole("button", { name: word }));
  }

  it.each([
    [
      { leaving_pending: 3, promoted_filtered: 0, discarded_filtered: 2 },
      "Takes 3 offers out of Pending. Loses none you promoted. 2 you discarded had it.",
    ],
    [
      { leaving_pending: 1, promoted_filtered: 1, discarded_filtered: 0 },
      "Takes 1 offer out of Pending. Would have filtered 1 you promoted. None you discarded had it.",
    ],
  ])("proposes excluding the word with the effect %o", async (preview, effect) => {
    // Arrange
    const user = userEvent.setup();
    inboxWith([lead()]);
    const asked = previewing(preview);
    renderInbox();

    // Act
    await chooseWord(user, "Lead Backend Engineer", "Lead");

    // Assert
    expect(screen.getByText("Exclude “Lead” from the profile Backend?")).toBeInTheDocument();
    expect(await screen.findByText(effect)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Only discard this one" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Discard and exclude “Lead”" })).toBeInTheDocument();
    expect(asked).toEqual([
      { search_profile_id: PROFILE_ID, excluded_keywords: ["Senior", "Lead"] },
    ]);
  });

  it.each([
    ["Only discard this one", false],
    ["Discard and exclude “Lead”", true],
  ])("%s discards the offer because of the word", async (choice, excludes) => {
    // Arrange
    const user = userEvent.setup();
    const candidate = lead();
    inboxWith([candidate]);
    previewing();
    const discarded: unknown[] = [];
    const edited: unknown[] = [];
    server.use(
      http.post("/api/v1/offers/:offerId/discard", async ({ params, request }) => {
        discarded.push({ offerId: params.offerId, ...((await request.json()) as object) });
        return HttpResponse.json({}, { status: 201 });
      }),
      http.post("/api/v1/criteria-changes", async ({ request }) => {
        edited.push(await request.json());
        return HttpResponse.json({}, { status: 201 });
      }),
    );
    // Through the change log (specs/inbox/criteria_changes.feature), from this offer.
    const edits = excludes
      ? [
          {
            search_profile_id: PROFILE_ID,
            excluded_keywords: ["Senior", "Lead"],
            offer_id: candidate.id,
          },
        ]
      : [];
    renderInbox();
    await chooseWord(user, "Lead Backend Engineer", "Lead");

    // Act
    await user.click(screen.getByRole("button", { name: choice }));

    // Assert
    expect(await screen.findByText("Offer discarded")).toBeInTheDocument();
    expect(discarded).toEqual([{ offerId: candidate.id, reason: "title_word", word: "Lead" }]);
    expect(edited).toEqual(edits);
  });
});

// specs/ui/inbox.feature: "Discarding opens the piece with the reasons" and "Discard an
// offer because of a word in its title".
describe("InboxPage discarding", () => {
  it("keeps the title as a link and offers its words under A word in the title", async () => {
    // Arrange
    const user = userEvent.setup();
    inboxWith([offer("Senior Backend Engineer")]);
    renderInbox();
    const piece = await openedPane("Senior Backend Engineer");

    // Act
    await user.click(within(piece).getByRole("button", { name: "Discard" }));

    // Assert
    const opened = await openedPane("Senior Backend Engineer");
    expect(within(opened).getByRole("heading", { name: "Senior Backend Engineer" })).toBeVisible();
    const words = within(opened).getByRole("group", { name: "A word in the title" });
    expect(
      within(words)
        .getAllByRole("button")
        .map((b) => b.textContent),
    ).toEqual(["Senior", "Backend", "Engineer"]);
  });

  it("a word of an offer without a profile discards it right away", async () => {
    // Arrange
    const user = userEvent.setup();
    const candidate = offer("Senior Backend Engineer");
    inboxWith([candidate]);
    const discarded: unknown[] = [];
    server.use(
      http.post("/api/v1/offers/:offerId/discard", async ({ request }) => {
        discarded.push(await request.json());
        return HttpResponse.json({}, { status: 201 });
      }),
    );
    renderInbox();
    const piece = await openedPane("Senior Backend Engineer");
    await user.click(within(piece).getByRole("button", { name: "Discard" }));
    const words = await screen.findByRole("group", { name: "A word in the title" });

    // Act
    await user.click(within(words).getByRole("button", { name: "Senior" }));

    // Assert
    expect(await screen.findByText("Offer discarded")).toBeInTheDocument();
    expect(discarded).toEqual([{ reason: "title_word", word: "Senior" }]);
  });
});

// specs/ui/inbox.feature: "A discarded offer leaves the inbox at once".
describe("InboxPage discarding with a slow inbox", () => {
  it("shows the message and takes the offer out without waiting for the inbox", async () => {
    // Arrange
    const user = userEvent.setup();
    inboxWith([offer("Backend Engineer")]);
    const release = slowToListAfterDiscard();
    renderInbox();
    const piece = await openedPane("Backend Engineer");
    await user.click(within(piece).getByRole("button", { name: "Discard" }));
    const reasons = await screen.findByRole("group", { name: "Discard because" });

    try {
      // Act
      await user.click(within(reasons).getByRole("button", { name: "No reason" }));

      // Assert
      expect(await screen.findByText("Offer discarded")).toBeInTheDocument();
      expect(screen.queryByRole("article", { name: "Backend Engineer" })).not.toBeInTheDocument();
    } finally {
      release();
    }
  });

  it("disables Cancel while the discard is being done", async () => {
    // Arrange
    const user = userEvent.setup();
    inboxWith([offer("Backend Engineer")]);
    let release!: () => void;
    const released = new Promise<void>((resolve) => {
      release = resolve;
    });
    server.use(
      http.post("/api/v1/offers/:offerId/discard", async () => {
        await released;
        return HttpResponse.json({}, { status: 201 });
      }),
    );
    renderInbox();
    const piece = await openedPane("Backend Engineer");
    await user.click(within(piece).getByRole("button", { name: "Discard" }));
    const reasons = await screen.findByRole("group", { name: "Discard because" });

    try {
      // Act
      await user.click(within(reasons).getByRole("button", { name: "No reason" }));

      // Assert
      expect(within(reasons).getByRole("button", { name: "Cancel" })).toBeDisabled();
    } finally {
      release();
    }
  });
});

// specs/ui/inbox.feature: "The titles that keep coming without a title of yours".
describe("InboxPage frequent titles", () => {
  it("lists them in Filtered and adds one as a criteria change", async () => {
    // Arrange
    const user = userEvent.setup();
    inboxWith([imported("Software Engineer, Backend", rulesWith(rule("title", "failed")))]);
    const preview = {
      entering_pending: 2,
      leaving_pending: 0,
      promoted_filtered: 0,
      discarded_filtered: 0,
    };
    const added: unknown[] = [];
    server.use(
      http.get("/api/v1/offers/frequent-titles", () =>
        HttpResponse.json({
          offers: 6,
          titles: [
            {
              title: "Software Engineer, Backend",
              offers: 3,
              with_keywords: 2,
              reading_passes: 1,
              titles: ["Backend Engineer", "Software Engineer, Backend"],
              preview,
            },
          ],
        }),
      ),
      http.post("/api/v1/criteria-changes", async ({ request }) => {
        added.push(await request.json());
        return HttpResponse.json({}, { status: 201 });
      }),
    );
    renderInbox("/inbox?status=filtered");
    const block = await screen.findByRole("region", {
      name: "No title of yours · 6 offers · Backend",
    });
    expect(within(block).getByText("Most frequent titles")).toBeInTheDocument();
    expect(
      within(block).getByText("2 mention python and django · 1 remote and open to Spain"),
    ).toBeInTheDocument();

    // Act
    await user.click(
      within(block).getByRole("button", { name: "Add title · brings 2 to Pending" }),
    );

    // Assert
    expect(added).toEqual([
      { search_profile_id: PROFILE_ID, titles: ["Backend Engineer", "Software Engineer, Backend"] },
    ]);
  });
});

// specs/ui/inbox.feature, "Triage": the E2E tests cannot reach the offer triager.
describe("InboxPage triage", () => {
  type Suggestion = components["schemas"]["CriteriaSuggestionRead"];

  /** An available triager answering these batches in order, the last one again after. */
  function triagerAnswering(
    ...batches: { triaged: number; ok: number; ko: number; to_rescue?: number; left: number }[]
  ) {
    let call = 0;
    server.use(
      http.get("/api/v1/offers/triager", () => HttpResponse.json({ is_available: true })),
      http.get("/api/v1/criteria-suggestions", () =>
        HttpResponse.json({ items: [], total: 0, limit: 100, offset: 0 }),
      ),
      http.post("/api/v1/offers/triages", () => {
        const batch = batches[Math.min(call, batches.length - 1)];
        call += 1;
        return HttpResponse.json({ failed: 0, to_rescue: 0, ...batch }, { status: 201 });
      }),
    );
  }

  /** The triager's suggestion to exclude "Lead" from Backend, coming from these offers. */
  function triagerSuggesting(...offerIds: string[]) {
    let suggestions: Suggestion[] = [
      {
        search_profile_id: PROFILE_ID,
        search_profile_name: "Backend",
        source: "triager",
        why: "You discard lead roles.",
        rule: "excluded_keywords",
        word: "Lead",
        after: ["Senior", "Lead"],
        offer_ids: offerIds,
        discarded: 5,
        preview: {
          entering_pending: 0,
          leaving_pending: 3,
          promoted_filtered: 0,
          discarded_filtered: 2,
          discarded_fitting: 0,
        },
      },
    ];
    const sent: { url: string; body: unknown }[] = [];
    server.use(
      http.get("/api/v1/offers/triager", () => HttpResponse.json({ is_available: true })),
      http.get("/api/v1/criteria-suggestions", () =>
        HttpResponse.json({ items: suggestions, total: suggestions.length, limit: 100, offset: 0 }),
      ),
      http.post(/\/api\/v1\/criteria-(changes|suggestions\/dismissals)$/, async ({ request }) => {
        sent.push({ url: new URL(request.url).pathname, body: await request.json() });
        suggestions = [];
        return HttpResponse.json({}, { status: 201 });
      }),
    );
    return sent;
  }

  it.each([
    [
      [
        { triaged: 5, ok: 2, ko: 3, left: 2 },
        { triaged: 2, ok: 1, ko: 1, left: 0 },
      ],
      "Triaged 7 · 3 OK · 4 KO · 0 left",
    ],
    [
      [
        { triaged: 3, ok: 1, ko: 2, left: 2 },
        { triaged: 0, ok: 0, ko: 0, left: 2 },
      ],
      "Triaged 3 · 1 OK · 2 KO · 2 left. Try again later.",
    ],
    [
      [
        { triaged: 5, ok: 2, ko: 3, to_rescue: 0, left: 4 },
        { triaged: 4, ok: 1, ko: 1, to_rescue: 2, left: 0 },
      ],
      "Triaged 9 · 3 OK · 4 KO · 2 to rescue · 0 left",
    ],
  ])("triages batch after batch until none is left or one triages none", async (batches, said) => {
    // Arrange
    const user = userEvent.setup();
    inboxWith([offer("Backend Engineer")]);
    triagerAnswering(...batches);
    renderInbox();

    // Act
    await user.click(await screen.findByRole("button", { name: "Triage with AI" }));

    // Assert
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent(said));
  });

  it("shows outstanding verdicts only while a triage request is pending", async () => {
    inboxWith([
      imported("Backend Engineer", rulesWith()),
      imported("Empty posting", rulesWith(), { hasDescription: false }),
    ]);
    triagerAnswering();
    let release!: () => void;
    const pending = new Promise<void>((resolve) => {
      release = resolve;
    });
    server.use(
      http.post("/api/v1/offers/triages", async () => {
        await pending;
        return HttpResponse.json({ triaged: 0, ok: 0, ko: 0, left: 1, failed: 1, to_rescue: 0 });
      }),
    );
    renderInbox();
    await userEvent.click(await screen.findByRole("button", { name: "Triage with AI" }));
    try {
      const indicator = await screen.findByText(/Awaiting verdict/);
      expect(indicator.closest("article")).toHaveAccessibleName("Backend Engineer");
    } finally {
      release();
    }
    await waitFor(() => expect(screen.queryByText(/Awaiting verdict/)).not.toBeInTheDocument());
  });

  it("shows the AI section of a triaged offer", async () => {
    // Arrange
    inboxWith([
      offer("Backend Engineer Lead", {
        company: "Globex",
        triage: {
          verdict: "ko",
          why_yes: { why: "A backend role.", quote: "Backend Engineer" },
          why_not: { why: "A part-time role.", quote: "Part-time, 20 hours a week" },
          confidence: "high",
        },
      }),
    ]);
    noCriteriaSuggestions();

    // Act
    renderInbox();

    // Assert
    const piece = await openedPane("Backend Engineer Lead");
    const section = within(piece).getByRole("region", { name: "AI verdict" });
    expect(section).toHaveTextContent("AI: KO");
    expect(within(section).getByRole("img", { name: "High confidence" })).toBeInTheDocument();
    expect(section).toHaveTextContent("Why yes: A backend role.");
    expect(section).toHaveTextContent("Why not: A part-time role.");
    expect(within(section).queryByText("View evidence")).not.toBeInTheDocument();
    expect(within(section).getByText("“Backend Engineer”")).toBeVisible();
    expect(within(section).getByText("“Part-time, 20 hours a week”")).toBeVisible();
  });

  it.each([
    ["no confidence", {}, null],
    ["medium confidence", { confidence: "medium" as const }, "Medium confidence"],
  ])("shows only what the triage has: %s", async (_case, fields, meter) => {
    // Arrange
    inboxWith([
      offer("Backend Engineer Lead", { triage: triaged("ok", "Like Acme's role.", fields) }),
    ]);
    noCriteriaSuggestions();

    // Act
    renderInbox();

    // Assert
    const piece = await openedPane("Backend Engineer Lead");
    const section = within(piece).getByRole("region", { name: "AI verdict" });
    expect(section).toHaveTextContent("Why yes: Like Acme's role.");
    expect(section).not.toHaveTextContent("Why not");
    expect(within(section).queryByRole("img")?.getAttribute("aria-label") ?? null).toBe(meter);
  });

  it.each([
    ["contract", "Part-time, 20 hours a week", "Discard: Contract"],
    ["title_word", "Lead", "Discard: A word in the title"],
    [null, null, null],
  ] as const)("shows a suggested discard %s as its action", async (reason, evidence, action) => {
    // Arrange
    inboxWith([
      offer("Backend Engineer Lead", {
        triage: triaged("ko", "Part-time role."),
        suggested_discard: reason && evidence ? { reason, evidence } : null,
      }),
    ]);
    noCriteriaSuggestions();

    // Act
    renderInbox();

    // Assert
    const piece = await openedPane("Backend Engineer Lead");
    const discard = within(piece).queryByRole("button", { name: /^Discard: / });
    expect(discard?.textContent ?? null).toBe(action);
  });

  it.each([
    ["contract", "Part-time, 20 hours a week", { reason: "contract" }],
    ["title_word", "Lead", { reason: "title_word", word: "Lead" }],
  ] as const)("discards as suggested because %s", async (reason, evidence, body) => {
    // Arrange
    const user = userEvent.setup();
    const suggested = offer("Backend Engineer Lead", {
      triage: triaged("ko", "Not for you."),
      suggested_discard: { reason, evidence },
    });
    inboxWith([suggested]);
    const discarded: unknown[] = [];
    server.use(
      http.get("/api/v1/criteria-suggestions", () =>
        HttpResponse.json({ items: [], total: 0, limit: 100, offset: 0 }),
      ),
      http.post("/api/v1/offers/:offerId/discard", async ({ params, request }) => {
        discarded.push({ offerId: params.offerId, ...((await request.json()) as object) });
        return HttpResponse.json({}, { status: 201 });
      }),
    );
    renderInbox();
    const piece = await openedPane("Backend Engineer Lead");

    // Act
    await user.click(within(piece).getByRole("button", { name: /^Discard: / }));

    // Assert
    expect(await screen.findByText("Offer discarded")).toBeInTheDocument();
    expect(discarded).toEqual([{ offerId: suggested.id, ...body }]);
  });

  // specs/ui/inbox.feature: "An offer discarded as suggested leaves the inbox at once".
  it("an offer discarded as suggested leaves the inbox at once", async () => {
    // Arrange
    const user = userEvent.setup();
    inboxWith([
      offer("Backend Engineer Lead", {
        triage: triaged("ko", "Not for you."),
        suggested_discard: { reason: "contract", evidence: "Part-time" },
      }),
    ]);
    noCriteriaSuggestions();
    const release = slowToListAfterDiscard();
    renderInbox();
    const piece = await openedPane("Backend Engineer Lead");

    try {
      // Act
      await user.click(within(piece).getByRole("button", { name: /^Discard: / }));

      // Assert
      expect(await screen.findByText("Offer discarded")).toBeInTheDocument();
      expect(
        screen.queryByRole("article", { name: "Backend Engineer Lead" }),
      ).not.toBeInTheDocument();
    } finally {
      release();
    }
  });

  it("improves the filter from the offer the suggestion comes from", async () => {
    // Arrange
    const user = userEvent.setup();
    const ko = offer("Lead Backend Engineer", { triage: triaged("ko", "A lead role.") });
    inboxWith([ko]);
    const sent = triagerSuggesting(ko.id);
    renderInbox();
    const piece = await openedPane("Lead Backend Engineer");
    expect(
      await within(piece).findByText("Improve the filter: exclude “Lead” from Backend"),
    ).toBeInTheDocument();

    // Act
    await user.click(within(piece).getByRole("button", { name: "Exclude it" }));

    // Assert
    expect(sent).toEqual([
      {
        url: "/api/v1/criteria-changes",
        body: {
          search_profile_id: PROFILE_ID,
          excluded_keywords: ["Senior", "Lead"],
          offer_id: ko.id,
        },
      },
    ]);
    await waitFor(() =>
      expect(within(piece).queryByText(/Improve the filter/)).not.toBeInTheDocument(),
    );
  });

  it.each([
    [
      "Not now",
      "/api/v1/criteria-suggestions/dismissals",
      { search_profile_id: PROFILE_ID, rule: "excluded_keywords", word: "Lead" },
    ],
    [
      "Exclude it",
      "/api/v1/criteria-changes",
      { search_profile_id: PROFILE_ID, excluded_keywords: ["Senior", "Lead"] },
    ],
  ])("shows the triager's suggestion above the offers, and %s", async (choice, url, body) => {
    // Arrange
    const user = userEvent.setup();
    inboxWith([offer("Backend Engineer")]);
    const sent = triagerSuggesting();
    renderInbox();
    const shown = await screen.findByRole("region", { name: "AI suggestion" });
    expect(within(shown).getByText("AI suggests: exclude “Lead” from Backend")).toBeInTheDocument();
    expect(
      within(shown).getByText("Takes 3 offers out of Pending, loses none you promoted."),
    ).toBeInTheDocument();

    // Act
    await user.click(within(shown).getByRole("button", { name: choice }));

    // Assert
    expect(sent).toEqual([{ url, body }]);
    await waitFor(() =>
      expect(screen.queryByRole("region", { name: "AI suggestion" })).not.toBeInTheDocument(),
    );
  });

  it("shows the verdict of a near miss and relaxes its rule from it", async () => {
    // Arrange
    const user = userEvent.setup();
    const nearMiss = offer("Senior Backend Engineer", {
      company: "Initech",
      filtered: true,
      filter_reason: {
        search_profile_id: PROFILE_ID,
        search_profile_name: "Backend",
        has_description: true,
        near_miss: true,
        rules: [
          {
            rule: "title",
            result: "passed",
            found: ["Backend Engineer"],
            missing: [],
            value: null,
            evidence: null,
          },
          {
            rule: "excluded",
            result: "failed",
            found: ["Senior"],
            missing: [],
            value: null,
            evidence: null,
          },
        ],
      },
      triage: triaged("ok", "Worth it."),
    });
    inboxWith([nearMiss]);
    let suggestions: Suggestion[] = [
      {
        search_profile_id: PROFILE_ID,
        search_profile_name: "Backend",
        source: "triager",
        why: "Worth it.",
        rule: "excluded_keywords",
        word: "Senior",
        after: [],
        offer_ids: [nearMiss.id],
        discarded: 5,
        preview: {
          entering_pending: 1,
          leaving_pending: 0,
          promoted_filtered: 0,
          discarded_filtered: 0,
          discarded_fitting: 0,
        },
      },
    ];
    const sent: unknown[] = [];
    server.use(
      http.get("/api/v1/offers/triager", () => HttpResponse.json({ is_available: true })),
      http.get("/api/v1/criteria-suggestions", () =>
        HttpResponse.json({ items: suggestions, total: suggestions.length, limit: 100, offset: 0 }),
      ),
      http.post("/api/v1/criteria-changes", async ({ request }) => {
        sent.push(await request.json());
        suggestions = [];
        return HttpResponse.json({}, { status: 201 });
      }),
    );
    renderInbox("/inbox?view=filtered");
    const piece = await openedPane("Senior Backend Engineer");
    expect(within(piece).getByRole("region", { name: "AI verdict" })).toHaveTextContent(
      "Why yes: Worth it.",
    );
    expect(
      await within(piece).findByText("Improve the filter: stop excluding “Senior” in Backend"),
    ).toBeInTheDocument();
    expect(
      within(piece).getByText("Brings 1 into Pending, none you discarded."),
    ).toBeInTheDocument();

    // Act
    await user.click(within(piece).getByRole("button", { name: "Relax it" }));

    // Assert
    expect(sent).toEqual([
      { search_profile_id: PROFILE_ID, excluded_keywords: [], offer_id: nearMiss.id },
    ]);
  });
});

describe("InboxPage triager discards", () => {
  const ids = ["0193a000-0000-7000-8000-0000000000a1", "0193a000-0000-7000-8000-0000000000a2"];

  /** "The triager would discard {n} offers": it says so, and discards them when asked. */
  function triagerWouldDiscard(count: number) {
    const sent = { discards: 0, restored: [] as string[] };
    server.use(
      http.get("/api/v1/offers/triager", () =>
        HttpResponse.json({ is_available: false, discardable: count }),
      ),
      http.post("/api/v1/offers/triager-discards", () => {
        sent.discards += 1;
        return HttpResponse.json(
          { discarded: ids.slice(0, count).length, offer_ids: ids.slice(0, count) },
          { status: 201 },
        );
      }),
      http.delete("/api/v1/offers/:offerId/discard", ({ params }) => {
        sent.restored.push(String(params.offerId));
        return new HttpResponse(null, { status: 204 });
      }),
    );
    return sent;
  }

  // specs/ui/inbox.feature, "Let the AI discard the offers it is sure of"
  it("lets the AI discard the offers it is sure of", async () => {
    // Arrange
    const user = userEvent.setup();
    inboxWith([]);
    const sent = triagerWouldDiscard(2);
    renderInbox();
    expect(
      await screen.findByText(
        "The ones it marked KO with high confidence. You can restore any of them.",
      ),
    ).toBeInTheDocument();

    // Act
    await user.click(await screen.findByRole("button", { name: "Let AI discard 2" }));

    // Assert
    expect(sent.discards).toBe(1);
    expect(await screen.findByText("AI discarded 2 offers")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Undo" })).toBeInTheDocument();
  });

  // specs/ui/inbox.feature, "Undo the AI's discards right away"
  it("undoes the AI's discards right away", async () => {
    // Arrange
    const user = userEvent.setup();
    inboxWith([]);
    const sent = triagerWouldDiscard(2);
    renderInbox();
    await user.click(await screen.findByRole("button", { name: "Let AI discard 2" }));

    // Act
    await user.click(await screen.findByRole("button", { name: "Undo" }));

    // Assert
    expect(await screen.findByText("Offers restored")).toBeInTheDocument();
    expect(sent.restored).toEqual(ids);
  });

  // specs/ui/inbox.feature, 'With nothing for the AI to discard there is no "Let AI discard"'
  it('without anything for the AI to discard there is no "Let AI discard"', async () => {
    // Arrange
    inboxWith([offer("Backend Engineer")]);
    triagerWouldDiscard(0);

    // Act
    renderInbox();

    // Assert
    expect(await screen.findByRole("article", { name: "Backend Engineer" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Let AI discard/ })).not.toBeInTheDocument();
  });

  // specs/ui/inbox.feature, "A triager discard says it is the AI's"
  it("says a triager discard is the AI's, and restores it", async () => {
    // Arrange
    inboxWith([
      offer("Backend Engineer", {
        status: "discarded",
        discard_reason: "contract",
        triager_discard: "discarded",
      }),
    ]);

    // Act
    renderInbox("/inbox?status=discarded");

    // Assert
    const piece = await openedPane("Backend Engineer");
    expect(piece).toHaveTextContent("Discarded by AI · Contract");
    expect(within(piece).getByRole("button", { name: "Restore" })).toBeInTheDocument();
  });

  // specs/ui/inbox.feature, "The reading pane shows the offer with the same parts"
  it("links the header of the pane to the original posting", async () => {
    // Arrange
    inboxWith([offer("Backend Engineer")]);

    // Act
    renderInbox();

    // Assert
    const piece = await screen.findByRole("article", { name: "Backend Engineer" });
    expect(within(piece).getByRole("link", { name: "Original posting" })).toHaveAttribute(
      "href",
      "https://remoteok.com/Backend Engineer",
    );
  });

  // specs/ui/inbox.feature, "A near miss with a verdict says it in its AI section"
  it.each([
    ["ok", true],
    ["ko", false],
  ] as const)("says a near miss is %s: worth rescuing is %s", async (verdict, rescue) => {
    // Arrange
    inboxWith([
      nearMiss("Backend Engineer", rule("stable", "failed", { value: false }), {
        triage: triaged(verdict, "Because."),
      }),
    ]);
    noCriteriaSuggestions();

    // Act
    renderInbox("/inbox?status=filtered");
    await userEvent.click(await screen.findByRole("button", { name: "Backend Engineer" }));

    // Assert
    const piece = await screen.findByRole("article", { name: "Backend Engineer" });
    expect(piece).toHaveTextContent("Near miss · filtered by one rule");
    const section = within(piece).getByRole("region", { name: "AI verdict" });
    expect(section.textContent?.includes("worth rescuing")).toBe(rescue);
  });
});

// specs/ui/inbox.feature, "What the row says"
describe("InboxPage row line", () => {
  /** The text of the row of an offer: its label and its line. */
  async function rowText(title: string): Promise<string> {
    const button = await within(offerList()).findByRole("button", { name: title });
    return button.closest("li")?.textContent ?? "";
  }

  it.each([
    ["promoted", "Promoted", "Application created"],
    ["discarded", "Discarded", "No reason"],
  ] as const)("a %s offer says %s and %s", async (status, label, line) => {
    // Arrange
    inboxWith([
      offer("Backend Engineer", {
        status,
        discard_reason: status === "discarded" ? "none" : null,
        application_id: status === "promoted" ? crypto.randomUUID() : null,
      }),
    ]);

    // Act
    renderInbox(`/inbox?status=${status}`);

    // Assert
    const text = await rowText("Backend Engineer");
    expect(text).toContain(label);
    expect(text).toContain(line);
  });

  it.each([
    ["ok", "high", "AI: OK · High", "Like Acme's role"],
    ["ko", "medium", "AI: KO · Medium", "A part-time role"],
  ] as const)(
    "a pending offer marked %s with %s confidence says %s",
    async (verdict, confidence, label, why) => {
      // Arrange
      inboxWith([offer("Backend Engineer", { triage: triaged(verdict, why, { confidence }) })]);
      noCriteriaSuggestions();

      // Act
      renderInbox();

      // Assert
      const text = await rowText("Backend Engineer");
      expect(text).toContain(label);
      expect(text).toContain(why);
    },
  );

  it.each([
    [
      "added by hand",
      offer("Backend Engineer", { job_board_id: null, job_board_name: null }),
      "Nothing to read: added by hand",
    ],
    [
      "from an email alert",
      imported("Backend Engineer", [TITLE_PASSES], {
        hasDescription: false,
        job_board_id: LINKEDIN_ID,
      }),
      "Nothing to read: email alert",
    ],
    [
      "with a reading",
      offer("Backend Engineer", {
        readings: [
          reading({
            work_mode: "remote",
            admits_location: true,
            location: "Spain",
            stable: true,
            stack: ["Python", "Django"],
          }),
        ],
      }),
      "Remote · Spain · Stable · Python, Django",
    ],
  ])("an offer %s says it was not triaged and %s", async (_case, pending, line) => {
    // Arrange
    inboxWith([pending], [BACKEND], [jobBoard(LINKEDIN_ID, "LinkedIn", "email")]);

    // Act
    renderInbox();

    // Assert
    const text = await rowText("Backend Engineer");
    expect(text).toContain("Not triaged");
    expect(text).toContain(line);
  });

  it.each([
    ["has no verdict", undefined, "Near miss"],
    ["was marked OK", triaged("ok", "Fits."), "AI: OK"],
  ])("a near miss that %s says %s and its failed rule", async (_case, triage, label) => {
    // Arrange
    inboxWith([
      nearMiss("Backend Engineer", rule("work_mode", "failed", { value: "hybrid" }), { triage }),
    ]);
    noCriteriaSuggestions();

    // Act
    renderInbox("/inbox");

    // Assert
    const text = await rowText("Backend Engineer");
    expect(text).toContain(label);
    expect(text).toContain("Mode: Hybrid, you ask Remote");
  });

  it("says a triager discard is the AI's", async () => {
    // Arrange
    inboxWith([
      offer("Backend Engineer", {
        status: "discarded",
        discard_reason: "contract",
        triager_discard: "discarded",
      }),
    ]);

    // Act
    renderInbox("/inbox?status=discarded");

    // Assert
    const text = await rowText("Backend Engineer");
    expect(text).toContain("Discarded by AI");
    expect(text).toContain("Contract");
  });
});

// specs/ui/inbox.feature: "The action bar says which offer of the view is open" and "The next
// offer opens after an action".
describe("InboxPage action bar", () => {
  const bar = () => within(readingPane()).getByRole("group", { name: "Offer actions" });

  it("says which offer of the view is open and offers Promote and Discard", async () => {
    // Arrange
    const user = userEvent.setup();
    inboxWith([offer("A"), offer("B"), offer("C")]);
    renderInbox();

    // Act
    await openRow(user, "B");

    // Assert
    expect(bar()).toHaveTextContent("2 of 3");
    expect(within(bar()).getByRole("button", { name: "Promote" })).toBeInTheDocument();
    expect(within(bar()).getByRole("button", { name: "Discard" })).toBeInTheDocument();
  });

  it.each([
    ["the next offer", "A", "B"],
    ["the previous one after the last", "C", "B"],
  ])("opens %s after discarding", async (_, discarded, next) => {
    // Arrange
    const user = userEvent.setup();
    inboxWith([offer("A"), offer("B"), offer("C")]);
    server.use(
      http.post("/api/v1/offers/:offerId/discard", () => HttpResponse.json({}, { status: 201 })),
    );
    renderInbox();
    await openRow(user, discarded);
    await user.click(within(bar()).getByRole("button", { name: "Discard" }));
    const reasons = within(readingPane()).getByRole("group", { name: "Discard because" });

    // Act
    await user.click(within(reasons).getByRole("button", { name: "No reason" }));

    // Assert
    expect(await screen.findByText("Offer discarded")).toBeInTheDocument();
    expect(await within(readingPane()).findByRole("article", { name: next })).toBeInTheDocument();
  });

  it("opens the next near miss after marking one as rightly filtered", async () => {
    // Arrange
    const user = userEvent.setup();
    const excluded = (word: string) => rule("excluded", "failed", { found: [word] });
    inboxWith([
      offer("Pending one"),
      nearMiss("Junior Backend Engineer", excluded("Junior")),
      nearMiss("Backend Intern", excluded("Intern")),
    ]);
    server.use(
      http.post("/api/v1/offers/:offerId/rightly-filtered", () =>
        HttpResponse.json({}, { status: 201 }),
      ),
    );
    renderInbox("/inbox?status=filtered");
    await openRow(user, "Junior Backend Engineer");
    expect(bar()).toHaveTextContent("1 of 2");

    // Act
    await user.click(within(bar()).getByRole("button", { name: "Rightly filtered" }));

    // Assert
    expect(await screen.findByText("Marked as rightly filtered")).toBeInTheDocument();
    expect(
      await within(readingPane()).findByRole("article", { name: "Backend Intern" }),
    ).toBeInTheDocument();
  });

  it("makes a suggested discard the main action, with Promote and Other reason", async () => {
    // Arrange
    const user = userEvent.setup();
    inboxWith([
      offer("Backend Engineer Lead", {
        triage: triaged("ko", "Part-time role."),
        suggested_discard: { reason: "contract", evidence: "Part-time" },
      }),
    ]);
    noCriteriaSuggestions();
    renderInbox();
    await openedPane("Backend Engineer Lead");
    expect(within(bar()).getByRole("button", { name: "Discard: Contract" })).toBeInTheDocument();
    expect(within(bar()).getByRole("button", { name: "Promote" })).toBeInTheDocument();

    // Act
    await user.click(within(bar()).getByRole("button", { name: "Other reason" }));

    // Assert
    expect(within(readingPane()).getByRole("group", { name: "Discard because" })).toBeVisible();
  });
});
