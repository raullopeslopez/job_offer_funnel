import { ThemeProvider } from "@mui/material";
import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { describe, expect, it } from "vitest";
import { theme } from "../theme";
import { PriorityBars } from "./PriorityBars";

function renderBars(ui: ReactElement) {
  return render(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

function barColors(img: HTMLElement) {
  return Array.from(img.children).map((bar) => getComputedStyle(bar).backgroundColor);
}

describe("PriorityBars", () => {
  it.each([
    ["high", 3],
    ["medium", 2],
    ["low", 1],
  ])("fills the bars for %s priority", (value, filled) => {
    // Arrange / Act
    renderBars(<PriorityBars value={value} />);

    // Assert
    const img = screen.getByRole("img", { name: `Priority ${value}` });
    const colors = barColors(img);
    expect(colors).toHaveLength(3);
    const filledColors = colors.slice(0, filled);
    expect(new Set(filledColors).size).toBe(1);
    expect(colors.slice(filled).every((c) => c !== filledColors[0])).toBe(true);
    expect(screen.getByText(value)).toBeInTheDocument();
  });

  it("hides the label with showLabel false", () => {
    // Arrange / Act
    renderBars(<PriorityBars value="high" showLabel={false} />);

    // Assert
    expect(screen.getByRole("img", { name: "Priority high" })).toBeInTheDocument();
    expect(screen.queryByText("high")).not.toBeInTheDocument();
  });

  it.each([null, undefined, ""])("shows a dash for %s", (value) => {
    // Arrange / Act
    renderBars(<PriorityBars value={value} />);

    // Assert
    expect(screen.getByText("—")).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });
});
