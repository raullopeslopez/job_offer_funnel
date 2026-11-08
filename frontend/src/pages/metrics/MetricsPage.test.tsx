import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { server } from "../../test/server";
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
