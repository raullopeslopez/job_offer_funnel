import { ThemeProvider } from "@mui/material";
import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { describe, expect, it } from "vitest";
import { theme } from "../theme";
import { StatusChip } from "./StatusChip";

function renderChip(ui: ReactElement) {
  return render(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

describe("StatusChip", () => {
  it.each([
    "discovered",
    "evaluated",
    "applied",
    "screening",
    "interviewing",
    "offer",
    "accepted",
    "rejected",
    "ghosted",
    "withdrawn",
    "offer_declined",
    "pending",
    "discarded",
    "promoted",
  ])("shows the raw value %s with an icon", (value) => {
    // Arrange / Act
    const { container } = renderChip(<StatusChip value={value} />);

    // Assert
    expect(screen.getByText(value)).toBeInTheDocument();
    expect(container.querySelector("svg[aria-hidden='true']")).not.toBeNull();
    expect(container.querySelector("[data-slot='dot']")).toBeNull();
  });

  it.each(["high", "medium", "low", "unknown_value"])(
    "shows a dot for %s, which has no icon",
    (value) => {
      // Arrange / Act
      const { container } = renderChip(<StatusChip value={value} />);

      // Assert
      expect(screen.getByText(value)).toBeInTheDocument();
      expect(container.querySelector("svg")).toBeNull();
      expect(container.querySelector("[data-slot='dot']")).not.toBeNull();
    },
  );

  it("shows a dot instead of the icon with icon={false}", () => {
    // Arrange / Act
    const { container } = renderChip(<StatusChip value="applied" icon={false} />);

    // Assert
    expect(container.querySelector("svg")).toBeNull();
    expect(container.querySelector("[data-slot='dot']")).not.toBeNull();
  });

  it.each([null, undefined, ""])("shows a dash for %j", (value) => {
    // Arrange / Act
    renderChip(<StatusChip value={value} />);

    // Assert
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
