import { ThemeProvider } from "@mui/material";
import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { describe, expect, it } from "vitest";
import { STAGES } from "../pages/applications/options";
import { theme } from "../theme";
import { StageProgress } from "./StageProgress";

function renderProgress(ui: ReactElement) {
  return render(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

function segmentColors(img: HTMLElement) {
  return Array.from(img.children).map((s) => getComputedStyle(s).backgroundColor);
}

describe("StageProgress", () => {
  it.each(STAGES.map((stage, i) => [stage, i + 1] as const))(
    "fills %s up to segment %i",
    (stage, n) => {
      // Arrange / Act
      renderProgress(<StageProgress stage={stage} />);

      // Assert
      const img = screen.getByRole("img", { name: `Stage ${n} of ${STAGES.length}` });
      const colors = segmentColors(img);
      expect(colors).toHaveLength(STAGES.length);
      const filled = colors.slice(0, n);
      expect(new Set(filled).size).toBe(1);
      expect(colors.slice(n).every((c) => c !== filled[0])).toBe(true);
    },
  );

  it("greys the filled segments and marks it closed when there is an outcome", () => {
    // Arrange
    renderProgress(<StageProgress stage="applied" />);
    const open = segmentColors(screen.getByRole("img"));

    // Act
    renderProgress(<StageProgress stage="applied" outcome="rejected" />);

    // Assert
    const closed = segmentColors(screen.getByRole("img", { name: /, closed$/ }));
    expect(closed[0]).not.toBe(open[0]);
    expect(closed[STAGES.length - 1]).toBe(open[STAGES.length - 1]);
  });

  it("uses a taller bar for the large size", () => {
    // Arrange / Act
    renderProgress(<StageProgress stage="applied" size="large" />);

    // Assert
    const img = screen.getByRole("img");
    expect(getComputedStyle(img.children[0] as Element).height).toBe("6px");
  });
});
