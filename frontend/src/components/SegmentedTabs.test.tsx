import { ThemeProvider } from "@mui/material";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { theme } from "../theme";
import { SegmentedTabs } from "./SegmentedTabs";

const items = [
  { value: "pending", label: "Pending", count: 12 },
  { value: "filtered", label: "Filtered", count: 40 },
  { value: "discarded", label: "Discarded", count: 3 },
];

function renderTabs(onChange = vi.fn()) {
  render(
    <ThemeProvider theme={theme}>
      <SegmentedTabs items={items} value="pending" onChange={onChange} aria-label="Offers" />
    </ThemeProvider>,
  );
  return onChange;
}

describe("SegmentedTabs", () => {
  it.each([
    ["Pending 12", "true"],
    ["Filtered 40", "false"],
    ["Discarded 3", "false"],
  ])("shows the tab %j with its count, selected=%s", (name, selected) => {
    // Arrange / Act
    renderTabs();

    // Assert
    expect(screen.getByRole("tab", { name })).toHaveAttribute("aria-selected", selected);
  });

  it("calls onChange with the value of the clicked tab", async () => {
    // Arrange
    const onChange = renderTabs();

    // Act
    await userEvent.click(screen.getByRole("tab", { name: "Filtered 40" }));

    // Assert
    expect(onChange).toHaveBeenCalledWith("filtered");
  });

  it("moves between tabs with the arrow keys", async () => {
    // Arrange
    renderTabs();
    screen.getByRole("tab", { name: "Pending 12" }).focus();

    // Act
    await userEvent.keyboard("{ArrowRight}");

    // Assert
    expect(screen.getByRole("tab", { name: "Filtered 40" })).toHaveFocus();
  });
});
