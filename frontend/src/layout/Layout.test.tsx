import { ThemeProvider } from "@mui/material";
import { fireEvent, render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { theme } from "../theme";
import { Layout } from "./Layout";
import { navItems } from "./navItems";

function renderLayout() {
  const router = createMemoryRouter([
    { element: <Layout />, children: [{ path: "*", element: null }] },
  ]);
  return render(
    <ThemeProvider theme={theme}>
      <RouterProvider router={router} />
    </ThemeProvider>,
  );
}

describe("Layout", () => {
  it("links every screen in the navigation", () => {
    // Arrange
    renderLayout();

    // Act
    const nav = screen.getByRole("navigation", { name: "Main" });

    // Assert
    for (const { label, path } of navItems) {
      expect(nav).toContainElement(screen.getByRole("link", { name: label }));
      expect(screen.getByRole("link", { name: label })).toHaveAttribute("href", path);
    }
  });

  it.each([
    ["Dark theme", "Light theme"],
    ["Light theme", "Dark theme"],
  ])("switches the label from %s to %s when the theme toggle is pressed", (before, after) => {
    // Arrange
    renderLayout();
    if (before === "Light theme")
      fireEvent.click(screen.getByRole("button", { name: "Dark theme" }));

    // Act
    fireEvent.click(screen.getByRole("button", { name: before }));

    // Assert
    expect(screen.getByRole("button", { name: after })).toBeInTheDocument();
    expect(screen.getByText(after)).toBeInTheDocument();
  });
});
