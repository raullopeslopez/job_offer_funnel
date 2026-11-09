import { ThemeProvider } from "@mui/material";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { server } from "../../test/server";
import { theme } from "../../theme";
import { formatRate } from "./ConversionSection";
import { MetricsPage } from "./MetricsPage";

// specs/ui/metrics.feature: the figures and the empty state are covered by the E2E.

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

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <ThemeProvider theme={theme}>
      <QueryClientProvider client={queryClient}>
        <MetricsPage />
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
    const [labelNode] = await screen.findAllByText(label);
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
        <MetricsPage />
      </QueryClientProvider>,
    );

    // Assert
    expect(await screen.findByText("The metrics could not be loaded")).toBeVisible();
  });
});
