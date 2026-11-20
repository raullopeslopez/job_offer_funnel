import { ThemeProvider } from "@mui/material";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { theme } from "../theme";
import { CardList } from "./CardList";

type Row = { id: string; name: string };

const rows = (count: number): Row[] =>
  Array.from({ length: count }, (_, i) => ({ id: String(i), name: `Row ${i + 1}` }));

function renderList(shown: Row[], total: number, page = 0, onPaginationChange = vi.fn()) {
  render(
    <ThemeProvider theme={theme}>
      <CardList
        aria-label="Things"
        rows={shown}
        rowKey={(row) => row.id}
        renderCard={(row) => row.name}
        total={total}
        loading={false}
        pagination={{ page, pageSize: 2 }}
        onPaginationChange={onPaginationChange}
        empty={<p>Nothing here</p>}
      />
    </ThemeProvider>,
  );
  return onPaginationChange;
}

describe("CardList", () => {
  it("shows a card per row", () => {
    // Arrange / Act
    renderList(rows(2), 2);

    // Assert
    const list = screen.getByRole("list", { name: "Things" });
    expect(
      within(list)
        .getAllByRole("listitem")
        .map((card) => card.textContent),
    ).toEqual(["Row 1", "Row 2"]);
    expect(screen.queryByRole("button", { name: "Go to next page" })).not.toBeInTheDocument();
  });

  it("shows what it is given when there are no rows", () => {
    // Arrange / Act
    renderList([], 0);

    // Assert
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  it.each([
    [0, "1–2 of 5", "Go to next page", 1],
    [2, "5–5 of 5", "Go to previous page", 1],
  ])("on page %i says %j and %s asks for page %i", async (page, range, button, asked) => {
    // Arrange
    const user = userEvent.setup();
    const onPaginationChange = renderList(rows(2), 5, page);

    // Act
    await user.click(screen.getByRole("button", { name: button }));

    // Assert
    expect(screen.getByText(range)).toBeInTheDocument();
    expect(onPaginationChange).toHaveBeenCalledWith({ page: asked, pageSize: 2 });
  });
});
