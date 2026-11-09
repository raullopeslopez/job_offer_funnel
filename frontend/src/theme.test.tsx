import { Box, ThemeProvider, useColorScheme } from "@mui/material";
import type { CssVarsTheme } from "@mui/material/styles";
import { act, render, screen } from "@testing-library/react";
import { theme, toneOf } from "./theme";

function ToneProbe() {
  const { mode, setMode } = useColorScheme();
  return (
    <>
      <Box sx={{ bgcolor: "tone.blue.bg", color: "tone.blue.fg" }}>tone sample</Box>
      <button type="button" onClick={() => setMode("dark")}>
        go dark
      </button>
      <output>{mode}</output>
    </>
  );
}

describe("theme tones", () => {
  it.each([
    ["light", "oklch(0.95 0.03 250)", "oklch(0.45 0.1 250)"],
    ["dark", "oklch(0.3 0.05 250)", "oklch(0.85 0.08 250)"],
  ] as const)("defines the %s blue tone", (scheme, bg, fg) => {
    // Arrange
    const palette = (theme as unknown as CssVarsTheme).colorSchemes[scheme]?.palette;

    // Act
    const tone = palette?.tone.blue;

    // Assert
    expect(tone).toEqual({ bg, fg });
  });

  it("resolves sx tones through CSS variables that change with the color scheme", async () => {
    // Arrange
    render(
      <ThemeProvider theme={theme}>
        <ToneProbe />
      </ThemeProvider>,
    );
    const sample = screen.getByText("tone sample");

    // Act
    await act(async () => screen.getByRole("button", { name: "go dark" }).click());

    // Assert
    expect(screen.getByRole("status")).toHaveTextContent("dark");
    expect(document.documentElement).toHaveAttribute("data-dark");
    expect(sample).toBeInTheDocument();
    expect(theme.vars?.palette.tone.blue.bg).toContain("var(--mui-palette-tone-blue-bg");
    expect(toneOf.interviewing).toBe("amber");
  });
});
