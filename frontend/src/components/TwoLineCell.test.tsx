import WorkOutlineOutlined from "@mui/icons-material/WorkOutlineOutlined";
import { ThemeProvider } from "@mui/material";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { theme } from "../theme";
import { IconTile } from "./IconTile";
import { Meta, Sep, TwoLineCell } from "./TwoLineCell";

const wrap = (ui: React.ReactElement) => render(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);

describe("TwoLineCell", () => {
  it("renders lead, primary and secondary with a decorative separator", () => {
    // Arrange / Act
    wrap(
      <TwoLineCell
        lead={<IconTile icon={WorkOutlineOutlined} tone="blue" />}
        primary="Engineer"
        secondary={
          <>
            <Meta icon={WorkOutlineOutlined}>Acme</Meta>
            <Sep />
            <Meta mono>remote</Meta>
          </>
        }
      />,
    );

    // Assert
    expect(screen.getByText("Engineer")).toBeInTheDocument();
    expect(screen.getByText("Acme")).toBeInTheDocument();
    expect(screen.getByText("remote")).toBeInTheDocument();
    expect(screen.getByText("·")).toHaveAttribute("aria-hidden", "true");
  });

  it("omits the secondary line when absent", () => {
    // Arrange / Act
    wrap(<TwoLineCell primary="Only" />);

    // Assert
    expect(screen.getByText("Only")).toBeInTheDocument();
  });
});
