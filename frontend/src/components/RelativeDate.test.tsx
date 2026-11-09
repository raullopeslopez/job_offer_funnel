import { ThemeProvider } from "@mui/material";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { theme } from "../theme";
import { RelativeDate } from "./RelativeDate";

const now = new Date("2026-03-05T12:00:00Z");

describe("RelativeDate", () => {
  it.each([
    ["2026-03-05", "today"],
    ["2026-03-04", "yesterday"],
    ["2026-03-01", "4d ago"],
    ["2026-02-19", "2w ago"],
    ["2026-01-10", "Jan 10, 2026"],
  ])("shows %s as %s", (value, expected) => {
    // Arrange / Act
    render(
      <ThemeProvider theme={theme}>
        <RelativeDate value={value} now={now} />
      </ThemeProvider>,
    );

    // Assert
    const time = screen.getByText(expected);
    expect(time.tagName).toBe("TIME");
    expect(time).toHaveAttribute("dateTime", value);
  });

  it.each([null, undefined, ""])("shows a dash for %j", (value) => {
    // Arrange / Act
    render(<RelativeDate value={value} now={now} />);

    // Assert
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
