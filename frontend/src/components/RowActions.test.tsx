import DeleteOutlineOutlined from "@mui/icons-material/DeleteOutlineOutlined";
import { ThemeProvider } from "@mui/material";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { theme } from "../theme";
import { RowAction, RowActions, rowActionsSx } from "./RowActions";

function renderActions(onClick = vi.fn()) {
  return render(
    <ThemeProvider theme={theme}>
      <RowActions>
        <RowAction icon={DeleteOutlineOutlined} label="Delete" onClick={onClick} />
      </RowActions>
    </ThemeProvider>,
  );
}

describe("RowActions", () => {
  it("finds the action by its accessible name and calls onClick", async () => {
    // Arrange
    const onClick = vi.fn();
    const { container } = renderActions(onClick);

    // Act
    await userEvent.click(screen.getByRole("button", { name: "Delete" }));

    // Assert
    expect(onClick).toHaveBeenCalledOnce();
    expect(container.querySelector(".row-actions")).not.toBeNull();
  });

  it("shows the label as a tooltip on hover", async () => {
    // Arrange
    renderActions();

    // Act
    await userEvent.hover(screen.getByRole("button", { name: "Delete" }));

    // Assert
    expect(await screen.findByRole("tooltip")).toHaveTextContent("Delete");
  });

  it.each(["@media (hover: hover)", "@media (hover: none)"])(
    "defines %s in rowActionsSx",
    (query) => {
      // Arrange / Act / Assert
      expect(rowActionsSx).toHaveProperty([query]);
    },
  );
});
