// Premium theme (v2): the only place for color, typography, spacing and shape.
import { alpha, createTheme } from "@mui/material/styles";
import type {} from "@mui/x-data-grid/themeAugmentation";

const heading = '"Newsreader", Georgia, serif';
const sans = '"Geist Sans", "Helvetica Neue", Arial, sans-serif';
export const mono = '"Geist Mono", ui-monospace, Menlo, monospace';

// Status tones for <Chip>: same lightness/chroma, hue varies.
// Used in sx as "tone.<name>.bg" / "tone.<name>.fg".
type ToneColors = { bg: string; fg: string };
export type Tone = "neutral" | "blue" | "indigo" | "teal" | "amber" | "green" | "red" | "orange";
type Tones = Record<Tone, ToneColors>;

declare module "@mui/material/styles" {
  interface Palette {
    tone: Tones;
  }
  interface PaletteOptions {
    tone?: Tones;
  }
}

const lightTones: Tones = {
  neutral: { bg: "#eeeff2", fg: "#4a4c57" },
  blue: { bg: "oklch(0.95 0.03 250)", fg: "oklch(0.45 0.1 250)" },
  indigo: { bg: "oklch(0.95 0.03 275)", fg: "oklch(0.45 0.1 275)" },
  teal: { bg: "oklch(0.95 0.03 195)", fg: "oklch(0.45 0.08 195)" },
  amber: { bg: "oklch(0.95 0.04 80)", fg: "oklch(0.47 0.09 70)" },
  green: { bg: "oklch(0.95 0.04 150)", fg: "oklch(0.45 0.1 150)" },
  red: { bg: "oklch(0.95 0.03 25)", fg: "oklch(0.5 0.14 25)" },
  orange: { bg: "oklch(0.95 0.04 50)", fg: "oklch(0.5 0.12 50)" },
};
const darkTones: Tones = {
  neutral: { bg: "#24252b", fg: "#b4b6c2" },
  blue: { bg: "oklch(0.3 0.05 250)", fg: "oklch(0.85 0.08 250)" },
  indigo: { bg: "oklch(0.3 0.06 275)", fg: "oklch(0.85 0.08 275)" },
  teal: { bg: "oklch(0.3 0.04 195)", fg: "oklch(0.85 0.07 195)" },
  amber: { bg: "oklch(0.32 0.05 75)", fg: "oklch(0.87 0.09 80)" },
  green: { bg: "oklch(0.3 0.05 150)", fg: "oklch(0.85 0.09 150)" },
  red: { bg: "oklch(0.3 0.06 25)", fg: "oklch(0.83 0.09 25)" },
  orange: { bg: "oklch(0.32 0.06 50)", fg: "oklch(0.85 0.09 55)" },
};

export const toneOf: Record<string, Tone> = {
  discovered: "neutral",
  evaluated: "blue",
  applied: "indigo",
  screening: "teal",
  interviewing: "amber",
  offer: "green",
  accepted: "green",
  rejected: "red",
  ghosted: "neutral",
  withdrawn: "neutral",
  offer_declined: "orange",
  high: "red",
  medium: "amber",
  low: "neutral",
  pending: "neutral",
  discarded: "neutral",
  promoted: "green",
};

export const theme = createTheme({
  cssVariables: { colorSchemeSelector: "data" },
  colorSchemes: {
    light: {
      palette: {
        primary: { main: "#3949ab", light: "#6b77c9", dark: "#2c3890" },
        secondary: { main: "#00897b" },
        background: { default: "#f6f6f8", paper: "#ffffff" },
        text: { primary: "#17181c", secondary: "#5f6170", disabled: "#a3a5b0" },
        divider: "#e7e7ec",
        action: { hover: "rgba(23,24,28,0.04)", selected: "rgba(57,73,171,0.08)" },
        tone: lightTones,
      },
    },
    dark: {
      palette: {
        primary: { main: "#8c97e6", light: "#b3baf0", dark: "#a7b0ef", contrastText: "#0e0f12" },
        secondary: { main: "#4db6ac" },
        error: { main: "#f2777a" },
        background: { default: "#0e0f12", paper: "#16171b" },
        text: { primary: "#ececf0", secondary: "#9b9daa", disabled: "#5e606b" },
        divider: "#25262c",
        action: { hover: "rgba(255,255,255,0.05)", selected: "rgba(140,151,230,0.14)" },
        tone: darkTones,
      },
    },
  },
  typography: {
    fontFamily: sans,
    fontSize: 14,
    h4: {
      fontFamily: heading,
      fontWeight: 500,
      fontSize: "2.375rem",
      lineHeight: 1.12,
      letterSpacing: "-0.015em",
    },
    h5: {
      fontFamily: heading,
      fontWeight: 500,
      fontSize: "1.5rem",
      lineHeight: 1.25,
      letterSpacing: "-0.01em",
    },
    h6: {
      fontFamily: heading,
      fontWeight: 500,
      fontSize: "1.25rem",
      lineHeight: 1.35,
      letterSpacing: "-0.005em",
    },
    body1: { fontSize: "0.9375rem", lineHeight: 1.55, letterSpacing: 0 },
    body2: { fontSize: "0.875rem", lineHeight: 1.5, letterSpacing: 0 },
    button: { textTransform: "none", fontWeight: 500, letterSpacing: "0.005em" },
    caption: { letterSpacing: "0.01em" },
  },
  spacing: 8,
  shape: { borderRadius: 10 },
  components: {
    MuiButton: {
      defaultProps: { disableElevation: false },
      styleOverrides: {
        contained: ({ theme }) => ({
          boxShadow: "0 1px 2px rgba(16,18,28,0.14), inset 0 1px 0 rgba(255,255,255,0.14)",
          "&:hover": {
            boxShadow: `0 4px 12px ${alpha(theme.palette.primary.main, 0.28)}, inset 0 1px 0 rgba(255,255,255,0.14)`,
          },
        }),
      },
    },
    MuiIconButton: { styleOverrides: { root: { borderRadius: 10 } } },
    MuiOutlinedInput: {
      styleOverrides: {
        root: ({ theme }) => ({ backgroundColor: theme.palette.background.paper }),
      },
    },
    MuiPaper: {
      styleOverrides: {
        rounded: { borderRadius: 14 },
        elevation1: { boxShadow: "0 1px 2px rgba(16,18,28,0.04), 0 0 0 1px rgba(16,18,28,0.06)" },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          borderRadius: 14,
          boxShadow: "0 24px 64px rgba(16,18,28,0.18), 0 0 0 1px rgba(16,18,28,0.06)",
        },
      },
    },
    MuiDialogActions: { styleOverrides: { root: { padding: "8px 16px 16px" } } },
    MuiTab: { styleOverrides: { root: { textTransform: "none", letterSpacing: 0, minWidth: 72 } } },
    MuiLink: { defaultProps: { underline: "hover" } },
    MuiListItemButton: {
      styleOverrides: {
        root: ({ theme }) => ({
          borderRadius: 8,
          margin: "1px 8px",
          "&.active": {
            backgroundColor: theme.palette.action.selected,
            color: theme.palette.primary.main,
            fontWeight: 500,
          },
        }),
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: ({ theme }) => ({
          fontSize: "0.75rem",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          color: theme.palette.text.secondary,
        }),
        body: { fontVariantNumeric: "tabular-nums" },
      },
    },
    MuiChip: {
      styleOverrides: { root: { borderRadius: 999, fontWeight: 500, height: 22, fontSize: 12 } },
    },
    MuiDataGrid: {
      styleOverrides: {
        root: ({ theme }) => ({
          borderRadius: 14,
          backgroundColor: theme.palette.background.paper,
          "--DataGrid-containerBackground": theme.palette.mode === "dark" ? "#1a1b20" : "#fafafb",
        }),
        columnHeaderTitle: ({ theme }) => ({
          fontSize: "0.75rem",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          color: theme.palette.text.secondary,
        }),
        columnSeparator: { display: "none" },
      },
    },
  },
});
