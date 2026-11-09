import { ThemeProvider } from "@mui/material";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { theme } from "../theme";
import { TabLabel } from "./TabLabel";

describe("TabLabel", () => {
  it.each([0, 7, 128])("shows the label with the count %d", (count) => {
    // Arrange / Act
    render(
      <ThemeProvider theme={theme}>
        <TabLabel label="Pending" count={count} />
      </ThemeProvider>,
    );

    // Assert
    expect(screen.getByText("Pending")).toBeInTheDocument();
    expect(screen.getByText(String(count))).toBeInTheDocument();
  });
});
