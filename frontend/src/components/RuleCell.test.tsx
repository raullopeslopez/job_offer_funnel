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
  it.each<[RuleState, string, string]>([
    ["pass", "Mode", "Hybrid"],
    ["unknown", "Mode", "Not stated"],
    ["failed", "Mode · filtered it", "Hybrid"],
  ])("shows a %s rule with label %j and value %j", (state, label, value) => {
    // Arrange / Act
    renderThemed(<RuleCell label="Mode" value="Hybrid" state={state} />);

    // Assert
    expect(screen.getByText(label)).toBeInTheDocument();
    expect(screen.getByText(value)).toBeInTheDocument();
  });

  it.each<RuleState>(["pass", "unknown", "failed"])(
    "tells the %s state apart by shape",
    (state) => {
      // Arrange / Act
      renderThemed(<RuleCell label="Title" value="Engineer" state={state} />);

      // Assert
      const cell = screen.getByText(/^Title/).parentElement as HTMLElement;
      const style = getComputedStyle(cell);
      expect(style.borderStyle).toBe(state === "unknown" ? "dashed" : "solid");
    },
  );

  it("shows a dash for a passing rule without a value", () => {
    // Arrange / Act
    renderThemed(<RuleCell label="Keywords" state="pass" />);

    // Assert
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});

describe("RuleStrip", () => {
  it("groups its cells and spans the merged one over several columns", () => {
    // Arrange / Act
    renderThemed(
      <RuleStrip>
        <RuleCell label="Title" value="Engineer" state="pass" />
        <RuleCell label="Keywords" value="python" state="pass" />
        <MergedRuleCell span={3}>No description to read</MergedRuleCell>
      </RuleStrip>,
    );

    // Assert
    expect(screen.getByRole("group", { name: "Rules" })).toBeInTheDocument();
    const merged = screen.getByText("No description to read");
    expect(getComputedStyle(merged).gridColumn).toContain("span 3");
    expect(getComputedStyle(merged).borderStyle).toBe("dashed");
  });
});
