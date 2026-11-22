import { ThemeProvider } from "@mui/material";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { delay, HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { server } from "../test/server";
import { theme } from "../theme";
import { Layout, WAKING_UP_AFTER_MS } from "./Layout";
import { navGroups } from "./navItems";

function pendingOffers(total: number) {
  server.use(
    http.get("/api/v1/offers", ({ request }) => {
      const query = new URL(request.url).searchParams;
      const isPendingCount =
        query.get("status") === "pending" &&
        query.get("filtered") === "false" &&
        query.get("limit") === "1";
      if (!isPendingCount) return HttpResponse.json({}, { status: 400 });
      return HttpResponse.json({ items: [], total, limit: 1, offset: 0 });
    }),
  );
}

function renderLayout() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter([
    { element: <Layout />, children: [{ path: "*", element: <p>Screen content</p> }] },
  ]);
  return render(
    <ThemeProvider theme={theme}>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </ThemeProvider>,
  );
}

describe("Layout", () => {
  it.each(navGroups.map((group) => [group.label, group.items.map((item) => item.label)] as const))(
    "links the screens of the %s group",
    (group, labels) => {
      // Arrange
      pendingOffers(0);
      renderLayout();

      // Act
      const list = screen.getByRole("list", { name: group });

      // Assert
      const links = within(list).getAllByRole("link");
      expect(links.map((link) => link.textContent?.replace(/\d+$/u, ""))).toEqual(labels);
    },
  );

  it("links every screen to its path", () => {
    // Arrange
    pendingOffers(0);
    renderLayout();

    // Act
    const nav = screen.getByRole("navigation", { name: "Main" });

    // Assert
    for (const { label, path } of navGroups.flatMap((group) => group.items)) {
      expect(within(nav).getByRole("link", { name: new RegExp(`^${label}`, "u") })).toHaveAttribute(
        "href",
        path,
      );
    }
  });

  it("shows the number of pending offers next to the inbox", async () => {
    // Arrange
    pendingOffers(7);

    // Act
    renderLayout();

    // Assert
    const inbox = screen.getByRole("link", { name: /^Inbox/u });
    expect(await within(inbox).findByLabelText("7 pending")).toHaveTextContent("7");
  });

  it.each([
    ["Dark theme", "Light theme"],
    ["Light theme", "Dark theme"],
  ])("switches the label from %s to %s when the theme toggle is pressed", (before, after) => {
    // Arrange
    pendingOffers(0);
    renderLayout();
    if (before === "Light theme")
      fireEvent.click(screen.getByRole("button", { name: "Dark theme" }));

    // Act
    fireEvent.click(screen.getByRole("button", { name: before }));

    // Assert
    expect(screen.getByRole("button", { name: after })).toBeInTheDocument();
    expect(screen.getByText(after)).toBeInTheDocument();
  });

  // specs/ui/waking_up.feature
  describe("while the API wakes up", () => {
    afterEach(() => vi.useRealTimers());

    function apiNeverAnswers() {
      server.use(http.get("/api/v1/offers", () => delay("infinite")));
    }

    it("covers the content until the API answers", () => {
      // Arrange
      apiNeverAnswers();

      // Act
      renderLayout();

      // Assert
      expect(screen.getByRole("progressbar", { name: "Loading" })).toBeVisible();
      expect(screen.getByText("Screen content")).not.toBeVisible();
    });

    it("says the server is waking up when the answer is slow", async () => {
      // Arrange
      vi.useFakeTimers({ shouldAdvanceTime: true });
      apiNeverAnswers();
      renderLayout();
      expect(screen.queryByText(/Waking up the server/u)).not.toBeInTheDocument();

      // Act
      await act(() => vi.advanceTimersByTimeAsync(WAKING_UP_AFTER_MS));

      // Assert
      expect(screen.getByText("Waking up the server. It can take up to a minute.")).toBeVisible();
    });

    it("shows the content once the API answers", async () => {
      // Arrange
      pendingOffers(3);

      // Act
      renderLayout();

      // Assert
      await waitFor(() => expect(screen.getByText("Screen content")).toBeVisible());
      expect(screen.queryByRole("progressbar", { name: "Loading" })).not.toBeInTheDocument();
    });

    it("offers to try again when the API fails, and shows the content when it answers", async () => {
      // Arrange
      server.use(http.get("/api/v1/offers", () => HttpResponse.json({}, { status: 503 })));
      renderLayout();
      const tryAgain = await screen.findByRole("button", { name: "Try again" });
      expect(screen.getByText("The server did not answer.")).toBeVisible();
      pendingOffers(3);

      // Act
      fireEvent.click(tryAgain);

      // Assert
      await waitFor(() => expect(screen.getByText("Screen content")).toBeVisible());
      expect(screen.queryByText("The server did not answer.")).not.toBeInTheDocument();
    });
  });
});
