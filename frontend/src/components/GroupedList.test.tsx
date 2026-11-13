import { ThemeProvider } from "@mui/material";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { theme } from "../theme";
import { GroupedList } from "./GroupedList";

describe("GroupedList", () => {
  it.each([
    [3, "Today · 3 offers"],
    [1, "Today · 1 offer"],
  ])("titles a group of %i as %j and shows its pieces", (count, heading) => {
    // Arrange / Act
    render(
      <ThemeProvider theme={theme}>
        <GroupedList title="Today" count={count}>
          <div>First</div>
          <div>Second</div>
        </GroupedList>
      </ThemeProvider>,
    );

    // Assert
    const group = screen.getByRole("region", { name: "Today" });
    expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
    expect(group).toHaveTextContent("First");
    expect(group).toHaveTextContent("Second");
  });
});
