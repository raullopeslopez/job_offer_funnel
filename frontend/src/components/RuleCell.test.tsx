import { ThemeProvider } from "@mui/material";
import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { describe, expect, it } from "vitest";
import { theme } from "../theme";
import { RuleCell, type RuleState } from "./RuleCell";
import { MergedRuleCell, RuleStrip } from "./RuleStrip";

function renderThemed(ui: ReactElement) {
  return render(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

describe("RuleCell", () => {
  it.each<[RuleState, string, boolean]>([
    ["pass", "Hybrid", false],
    ["unknown", "Not stated", false],
    ["failed", "Hybrid", true],
  ])("shows a %s rule with value %j, marked as filtered: %s", (state, value, marked) => {
    // Arrange / Act
    renderThemed(<RuleCell label="Mode" value="Hybrid" state={state} />);

    // Assert
    expect(screen.getByText("Mode")).toBeInTheDocument();
    expect(screen.getByText(value)).toBeInTheDocument();
    expect(screen.queryByText("filtered it") !== null).toBe(marked);
  });

  it.each<[RuleState, string]>([
    ["pass", "filled"],
    ["unknown", "hollow"],
    ["failed", "filled"],
  ])("tells the %s state apart by the shape of its dot: %s", (state, shape) => {
    // Arrange / Act
    renderThemed(<RuleCell label="Title" value="Engineer" state={state} />);

    // Assert
    const dot = screen.getByText("Title").firstElementChild as HTMLElement;
    expect(dot).toHaveAttribute("data-dot", shape);
  });

  it("shows the evidence of a failed rule under its value", () => {
    // Arrange / Act
    renderThemed(
      <RuleCell label="Mode" value="On-site" state="failed" evidence="Five days in Bilbao" />,
    );

    // Assert
    expect(screen.getByText("“Five days in Bilbao”")).toBeInTheDocument();
  });

  it("shows a dash for a passing rule without a value", () => {
    // Arrange / Act
    renderThemed(<RuleCell label="Keywords" state="pass" />);

    // Assert
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});

describe("RuleStrip", () => {
  it("lists its cells under a Rules heading, with the merged one as a line", () => {
    // Arrange / Act
    renderThemed(
      <RuleStrip>
        <RuleCell label="Title" value="Engineer" state="pass" />
        <RuleCell label="Keywords" value="python" state="pass" />
        <MergedRuleCell>No description to read</MergedRuleCell>
      </RuleStrip>,
    );

    // Assert
    expect(screen.getByRole("heading", { name: "Rules" })).toBeInTheDocument();
    expect(screen.getAllByRole("term").map((term) => term.textContent)).toEqual([
      "Title",
      "Keywords",
    ]);
    expect(screen.getByText("No description to read").closest("[data-state]")).toHaveAttribute(
      "data-state",
      "unknown",
    );
  });
});
