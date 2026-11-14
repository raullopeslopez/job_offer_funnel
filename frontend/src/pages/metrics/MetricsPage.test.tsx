import { ThemeProvider } from "@mui/material";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { MemoryRouter } from "react-router";
import type { components } from "../../api/schema";
import { server } from "../../test/server";
import { theme } from "../../theme";
import { formatRate } from "./ConversionSection";
import { describeChange } from "./CriteriaChanges";
import { MetricsPage } from "./MetricsPage";

// specs/ui/metrics.feature: the funnel figures and the empty state are covered by the E2E;
// the offer quality (@component) here, as the E2E data are all added today.

describe("formatRate", () => {
  it.each([
    [75, "75.0%"],
    [66.7, "66.7%"],
    [0, "0.0%"],
    [null, "—"],
  ])("shows %s as %s", (rate, shown) => {
    // Arrange, Act
    const result = formatRate(rate);

    // Assert
    expect(result).toBe(shown);
  });
});

const step = (from_stage: string, to_stage: string, rate: number | null) => ({
  from_stage,
  to_stage,
  reached_from: rate === null ? 0 : 4,
  reached_to: rate === null ? 0 : 3,
  rate,
});

function renderPage(path = "/metrics?view=funnel") {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <ThemeProvider theme={theme}>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[path]}>
          <MetricsPage />
        </MemoryRouter>
      </QueryClientProvider>
    </ThemeProvider>,
  );
}

describe("MetricsPage key figures", () => {
  it.each([
    ["Active", "7"],
    ["Interviewing", "3"],
    ["Response rate", "75.0%"],
    ["Offers", "2"],
  ])("shows the %s tile as %s", async (label, value) => {
    // Arrange
    server.use(
      http.get("/api/v1/metrics/conversion", () =>
        HttpResponse.json({ steps: [step("applied", "screening", 75)] }),
      ),
      http.get("/api/v1/metrics/conversion-by-channel", () => HttpResponse.json({ channels: [] })),
      http.get("/api/v1/metrics/pipeline", () =>
        HttpResponse.json({
          stages: [
            { stage: "interviewing", applications: 3 },
            { stage: "offer", applications: 2 },
          ],
          total: 7,
        }),
      ),
    );

    // Act
    renderPage();

    // Assert
    // The tiles come first; the chart legend can repeat a label such as "Active".
    const [labelNode] = await screen.findAllByText(label, { selector: "p" });
    expect(labelNode?.parentElement?.parentElement).toHaveTextContent(value);
  });

  it("shows a dash as the response rate when the rate is null", async () => {
    // Arrange
    server.use(
      http.get("/api/v1/metrics/conversion", () =>
        HttpResponse.json({
          steps: [step("saved", "applied", 50), step("applied", "screening", null)],
        }),
      ),
      http.get("/api/v1/metrics/conversion-by-channel", () => HttpResponse.json({ channels: [] })),
      http.get("/api/v1/metrics/pipeline", () => HttpResponse.json({ stages: [], total: 1 })),
    );

    // Act
    renderPage();

    // Assert
    const tile = (await screen.findByText("Response rate")).parentElement?.parentElement;
    expect(tile).toHaveTextContent("—");
  });
});

describe("MetricsPage", () => {
  it("says so when the metrics cannot be loaded", async () => {
    // Arrange
    const problem = { type: "about:blank", title: "Internal Server Error", status: 500 };
    server.use(
      http.get("/api/v1/metrics/conversion", () => HttpResponse.json(problem, { status: 500 })),
      http.get("/api/v1/metrics/conversion-by-channel", () => HttpResponse.json({ channels: [] })),
      http.get("/api/v1/metrics/pipeline", () => HttpResponse.json({ stages: [], total: 0 })),
    );
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    // Act
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/metrics?view=funnel"]}>
          <MetricsPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    // Assert
    expect(await screen.findByText("The metrics could not be loaded")).toBeVisible();
  });
});

type Quality = components["schemas"]["OfferQualityRead"];
type Figures = components["schemas"]["QualityFiguresRead"];

const figures = (fields: Partial<Figures> = {}): Figures => ({
  decided: 0,
  promoted_from_pending: 0,
  precision: null,
  reviewed_near_misses: 0,
  rescued_near_misses: 0,
  losses: null,
  fitting: 0,
  promoted: 0,
  applied: 0,
  answered: 0,
  suggested_decided: 0,
  suggested_discarded: 0,
  triager_precision: null,
  triaged_discarded: 0,
  missed_discards: 0,
  triager_misses: null,
  ...fields,
});

function qualityOf(total: Figures, fields: Partial<Quality> = {}) {
  const quality: Quality = {
    starts_on: "2026-02-11",
    total,
    weeks: ["2026-02-11", "2026-02-18", "2026-02-25", "2026-03-04"].map((starts_on) => ({
      starts_on,
      ...figures(),
    })),
    fitting_per_week: 0,
    near_misses_left: 0,
    discard_reasons: [],
    sources: [],
    ...fields,
  };
  server.use(
    http.get("/api/v1/offers/quality", () => HttpResponse.json(quality)),
    http.get("/api/v1/criteria-changes", () => HttpResponse.json(changesPage([]))),
    http.get("/api/v1/criteria-suggestions", () =>
      HttpResponse.json({ items: [], total: 0, limit: 100, offset: 0 }),
    ),
  );
}

type Change = components["schemas"]["CriteriaChangeRead"];

const changesPage = (items: Change[]) => ({ items, total: items.length, limit: 100, offset: 0 });

const change = (fields: Partial<Change>): Change => ({
  id: "0193a000-0000-7000-8000-000000000001",
  search_profile_id: "0193a000-0000-7000-8000-000000000002",
  search_profile_name: "Backend",
  offer_id: null,
  rule: "excluded_keywords",
  before: ["Senior"],
  after: ["Senior", "Lead"],
  entering_pending: 0,
  leaving_pending: 6,
  promoted_filtered: 0,
  discarded_filtered: 2,
  created_at: new Date().toISOString(),
  ...fields,
});

const card = async (label: string) => screen.findByRole("link", { name: label });

describe("MetricsPage offer quality", () => {
  it("opens on the offer quality, with the four key results", async () => {
    // Arrange
    qualityOf(
      figures({
        decided: 3,
        promoted_from_pending: 1,
        precision: 33.3,
        reviewed_near_misses: 2,
        rescued_near_misses: 1,
        losses: 50,
        fitting: 6,
        promoted: 2,
        applied: 2,
        answered: 1,
      }),
      { fitting_per_week: 1.5, near_misses_left: 4 },
    );

    // Act
    renderPage("/metrics");

    // Assert
    expect(await screen.findByRole("heading", { name: "Offer quality" })).toBeInTheDocument();
    expect(await card("Precision")).toHaveTextContent("33.3%1 promoted of 3 decided from Pending");
    expect(await card("Precision")).toHaveAttribute("href", "/inbox");
    expect(await card("Losses")).toHaveTextContent(
      "50.0%1 rescued of 2 near misses reviewed · 4 to review",
    );
    expect(await card("Losses")).toHaveAttribute("href", "/inbox?status=filtered");
    expect(await card("Flow")).toHaveTextContent("1.5/week6 new offers that fit in 4 weeks");
    expect(await card("Flow")).toHaveAttribute("href", "/sources");
    expect(await card("Real result")).toHaveTextContent("2 applied1 answered of 2 promoted");
  });

  it("shows a dash on each card without data, never 0%", async () => {
    // Arrange
    qualityOf(figures());

    // Act
    renderPage("/metrics");

    // Assert
    for (const label of ["Precision", "Losses", "Flow", "Real result"]) {
      const value = (await card(label)).querySelector("div");
      expect(value).toHaveTextContent("—");
    }
  });

  it("lists why you discard, the most frequent first, and what each source brought", async () => {
    // Arrange
    qualityOf(figures(), {
      discard_reasons: [
        { reason: "stack", offers: 2 },
        { reason: "location", offers: 1 },
      ],
      sources: [{ source: "Remote OK", imported: 5, fitting: 3, promoted: 1, discarded: 1 }],
    });

    // Act
    renderPage("/metrics");

    // Assert
    const reasons = await screen.findByRole("list", { name: "Why you discard" });
    expect(Array.from(reasons.children).map((item) => item.textContent)).toEqual([
      "Stack2",
      "Location1",
    ]);
    const row = within(screen.getByRole("table", { name: "By source" })).getAllByRole("row")[1];
    expect(row).toHaveTextContent("Remote OK5311");
  });

  it("shows the triager's precision and misses", async () => {
    // Arrange
    qualityOf(
      figures({
        suggested_decided: 4,
        suggested_discarded: 3,
        triager_precision: 75,
        triaged_discarded: 4,
        missed_discards: 1,
        triager_misses: 25,
      }),
    );

    // Act
    renderPage("/metrics");

    // Assert
    const triage = await screen.findByRole("region", { name: "The AI triage" });
    expect(triage).toHaveTextContent("75.0%");
    expect(triage).toHaveTextContent("3 right of 4 suggested discards you decided");
    expect(triage).toHaveTextContent("25.0%");
    expect(triage).toHaveTextContent("1 missed of 4 triaged offers you discarded");
  });

  it("shows no AI triage without triaged offers decided", async () => {
    // Arrange
    qualityOf(figures());

    // Act
    renderPage("/metrics");

    // Assert
    expect(await screen.findByRole("heading", { name: "Offer quality" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "The AI triage" })).not.toBeInTheDocument();
  });
});

describe("describeChange", () => {
  it.each([
    [change({}), "Excluded “Lead”"],
    [change({ before: ["Senior", "Lead"], after: ["Senior"] }), "Stopped excluding “Lead”"],
    [change({ rule: "titles", before: ["A"], after: ["A", "B"] }), "Added the title “B”"],
    [change({ rule: "keywords", before: ["Go"], after: [] }), "Removed the keyword “Go”"],
    [change({ rule: "location", before: null, after: "Spain" }), "Location: Spain"],
    [change({ rule: "work_modes", before: ["remote"], after: [] }), "Any work mode"],
  ])("describes %o as %s", (given, described) => {
    // Act
    const result = describeChange(given);

    // Assert
    expect(result).toBe(described);
  });
});

// specs/ui/metrics.feature: "Changes to your criteria".
describe("MetricsPage criteria changes", () => {
  it("lists each change with what it did, and undoes it", async () => {
    // Arrange
    const user = userEvent.setup();
    qualityOf(figures());
    const undone: unknown[] = [];
    let changes = [change({})];
    server.use(
      http.get("/api/v1/criteria-changes", () => HttpResponse.json(changesPage(changes))),
      http.delete("/api/v1/criteria-changes/:changeId", ({ params }) => {
        undone.push(params.changeId);
        changes = [];
        return new HttpResponse(null, { status: 204 });
      }),
    );
    renderPage("/metrics");
    const list = await screen.findByRole("list", { name: "Changes to your criteria" });
    expect(await within(list).findByText("Excluded “Lead”")).toBeInTheDocument();
    expect(
      within(list).getByText("Today · took 6 out of Pending · lost 0 promoted"),
    ).toBeInTheDocument();

    // Act
    await user.click(within(list).getByRole("button", { name: "Undo" }));

    // Assert
    expect(undone).toEqual([change({}).id]);
    expect(await screen.findByText("No changes yet.")).toBeInTheDocument();
  });
});

// specs/ui/metrics.feature: "A suggested exclusion, with "Not now" and "Exclude it"".
describe("MetricsPage suggested exclusions", () => {
  type Suggestion = components["schemas"]["CriteriaSuggestionRead"];
  const suggestion: Suggestion = {
    search_profile_id: "0193a000-0000-7000-8000-000000000002",
    search_profile_name: "Backend",
    word: "Lead",
    excluded_keywords: ["Senior", "Lead"],
    offer_ids: ["0193a000-0000-7000-8000-00000000000a", "0193a000-0000-7000-8000-00000000000b"],
    discarded: 5,
    preview: {
      entering_pending: 0,
      leaving_pending: 3,
      promoted_filtered: 0,
      discarded_filtered: 2,
    },
  };

  it.each([
    [
      "Not now",
      "/api/v1/criteria-suggestions/dismissals",
      { search_profile_id: suggestion.search_profile_id, word: "Lead" },
    ],
    [
      "Exclude it",
      "/api/v1/criteria-changes",
      { search_profile_id: suggestion.search_profile_id, excluded_keywords: ["Senior", "Lead"] },
    ],
  ])("%s sends what the suggestion says and hides it", async (button, url, body) => {
    // Arrange
    const user = userEvent.setup();
    qualityOf(figures(), { discard_reasons: [{ reason: "title_word", offers: 5 }] });
    let suggestions = [suggestion];
    const sent: unknown[] = [];
    server.use(
      http.get("/api/v1/criteria-suggestions", () =>
        HttpResponse.json({ items: suggestions, total: suggestions.length, limit: 100, offset: 0 }),
      ),
      http.post(url, async ({ request }) => {
        sent.push(await request.json());
        suggestions = [];
        return HttpResponse.json({}, { status: 201 });
      }),
    );
    renderPage("/metrics");
    const list = await screen.findByRole("list", { name: "Suggestions" });
    expect(within(list).getByText("Suggested: exclude “Lead” from Backend")).toBeInTheDocument();
    expect(
      within(list).getByText(
        "In 2 of the 5. Takes 3 offers out of Pending, loses none you promoted.",
      ),
    ).toBeInTheDocument();

    // Act
    await user.click(within(list).getByRole("button", { name: button }));

    // Assert
    expect(sent).toEqual([body]);
    await waitFor(() =>
      expect(screen.queryByRole("list", { name: "Suggestions" })).not.toBeInTheDocument(),
    );
  });
});
