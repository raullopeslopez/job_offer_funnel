import { ThemeProvider } from "@mui/material";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { theme } from "../../theme";
import { ApplicationsGrid } from "./ApplicationsGrid";
import type { Application } from "./options";

const application: Application = {
  id: "0b6a3f0e-0000-4000-8000-000000000001",
  company_id: "0b6a3f0e-0000-4000-8000-000000000002",
  company_name: "Internationalization Holdings GmbH",
  role: "Software Engineer II, Developer Productivity & Internal Tooling",
  channel: "referral",
  priority: "high",
  url: null,
  notes: null,
  stage: "interviewing",
  outcome: null,
  created_at: new Date().toISOString(),
};

// A phone: every media query of the breakpoints "down" matches.
function onAPhone() {
  vi.stubGlobal(
    "matchMedia",
    (query: string) =>
      ({
        matches: true,
        media: query,
        onchange: null,
        addEventListener: () => {},
        removeEventListener: () => {},
        addListener: () => {},
        removeListener: () => {},
        dispatchEvent: () => false,
      }) as MediaQueryList,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("ApplicationsGrid on a phone", () => {
  it("shows each application as a card with its role, company, channel and stage", () => {
    // Arrange
    onAPhone();

    // Act
    render(
      <ThemeProvider theme={theme}>
        <MemoryRouter>
          <ApplicationsGrid
            applications={[application]}
            total={1}
            loading={false}
            pagination={{ page: 0, pageSize: 20 }}
            onPaginationChange={() => {}}
          />
        </MemoryRouter>
      </ThemeProvider>,
    );

    // Assert
    const [card] = within(screen.getByRole("list", { name: "Applications" })).getAllByRole(
      "listitem",
    );
    expect(
      within(card as HTMLElement).getByRole("link", { name: application.role }),
    ).toHaveAttribute("href", `/applications/${application.id}`);
    expect(card).toHaveTextContent("Internationalization Holdings GmbH");
    expect(card).toHaveTextContent("referral");
    expect(card).toHaveTextContent("interviewing");
    expect(screen.queryByRole("grid")).not.toBeInTheDocument();
  });
});
