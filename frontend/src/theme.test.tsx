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

  it.each([
    ["light", "api", "oklch(0.58 0.17 255)", "oklch(0.955 0.03 255)", "oklch(0.44 0.17 255)"],
    ["light", "manual", "#8a8d98", "#eeeef1", "#4a4d57"],
    ["dark", "email", "oklch(0.5 0.2 300)", "oklch(0.3 0.05 300)", "oklch(0.85 0.08 300)"],
  ] as const)("defines the %s %s source color", (scheme, source, solid, tint, text) => {
    // Arrange
    const palette = (theme as unknown as CssVarsTheme).colorSchemes[scheme]?.palette;

    // Act
    const colors = palette?.source[source];

    // Assert
    expect(colors).toEqual({ solid, tint, text });
  });

  it.each([
    ["primary.main", "#111318"],
    ["background.default", "#f7f7f8"],
    ["text.secondary", "#60636e"],
    ["divider", "#e6e6ea"],
  ] as const)("uses the ink neutral %s in light", (path, color) => {
    // Arrange
    const palette = (theme as unknown as CssVarsTheme).colorSchemes.light?.palette;

    // Act
    const value = path
      .split(".")
      .reduce<unknown>((node, key) => (node as Record<string, unknown>)[key], palette);

    // Assert
    expect(value).toBe(color);
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
    expect(theme.vars?.palette.source.api.tint).toContain("var(--mui-palette-source-api-tint");
  });
});

// The fields and the lines of the overrides follow the color scheme: a white field in dark mode
// was the bug.
describe("theme overrides", () => {
  it("take their colors from the CSS variables", () => {
    // Arrange
    const overrides = theme.components?.MuiOutlinedInput?.styleOverrides?.root;

    // Act
    const style = typeof overrides === "function" ? overrides({ theme } as never) : overrides;

    // Assert
    expect(style).toMatchObject({
      backgroundColor: expect.stringContaining("var(--mui-palette-background-paper"),
    });
  });
});
