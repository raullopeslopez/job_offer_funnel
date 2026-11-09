import InboxOutlined from "@mui/icons-material/InboxOutlined";
import { ThemeProvider } from "@mui/material";
import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { describe, expect, it } from "vitest";
import { theme } from "../theme";
import { EmptyState } from "./EmptyState";

function renderUi(ui: ReactElement) {
  return render(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

describe("EmptyState", () => {
  it("shows the title, the help text and a decorative icon", () => {
    // Arrange / Act
    const { container } = renderUi(
      <EmptyState icon={InboxOutlined} title="Nothing here" text="Add one to get started." />,
    );

    // Assert
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
    expect(screen.getByText("Add one to get started.")).toBeInTheDocument();
    expect(container.querySelector("svg[aria-hidden='true']")).not.toBeNull();
  });

  it("omits the help text when not given", () => {
    // Arrange / Act
    renderUi(<EmptyState icon={InboxOutlined} title="Nothing here" />);

    // Assert
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
    expect(screen.queryByText("Add one to get started.")).toBeNull();
  });
});
