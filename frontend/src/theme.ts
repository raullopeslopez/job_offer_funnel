// "Ink and signal" theme (v3): the only place for color, typography, spacing and shape.
// Neutrals and ink carry the interface; the only saturated color tells where an offer came from.
import { createTheme } from "@mui/material/styles";
import type {} from "@mui/x-data-grid/themeAugmentation";

const sans = '"Geist Sans", "Helvetica Neue", Arial, sans-serif';
export const mono = '"Geist Mono", ui-monospace, Menlo, monospace';

// Status tones for <Chip>: same lightness/chroma, hue varies.
// Used in sx as "tone.<name>.bg" / "tone.<name>.fg".
type ToneColors = { bg: string; fg: string };
export type Tone = "neutral" | "blue" | "indigo" | "teal" | "amber" | "green" | "red" | "orange";
type Tones = Record<Tone, ToneColors>;

// Where an offer came from. Used in sx as "source.<name>.solid" / ".tint" / ".text",
// always next to the source's icon and label, never as color alone.
type SourceColors = { solid: string; tint: string; text: string };
export type Source = "api" | "rss" | "email" | "watched" | "manual";
type Sources = Record<Source, SourceColors>;

declare module "@mui/material/styles" {
  interface Palette {
    tone: Tones;
    source: Sources;
    // Neutral fill of a passing rule cell. Used in sx as "fill".
    fill: string;
  }
  interface PaletteOptions {
    tone?: Tones;
    source?: Sources;
    fill?: string;
  }
}

// Shape and type of the offer pieces (Epic #74, section 3). Radii and gaps as strings,
// so sx does not multiply them by shape.borderRadius or spacing.
export const offerShape = {
  tagHeight: 26,
  tagRadius: "7px",
  pieceGap: "3px",
  pieceRadius: "6px",
  groupRadius: "20px",
  ruleGap: "6px",
  iconSize: 13,
} as const;

export const offerType = {
  tag: { fontSize: "0.78125rem", fontWeight: 500 },
  cellLabel: {
    fontSize: "0.65625rem",
    fontWeight: 500,
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  cellValue: { fontSize: "0.8125rem" },
} as const;

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

const lightSources: Sources = {
  api: {
    solid: "oklch(0.58 0.17 255)",
    tint: "oklch(0.955 0.03 255)",
    text: "oklch(0.44 0.17 255)",
  },
  rss: { solid: "oklch(0.74 0.15 62)", tint: "oklch(0.955 0.04 62)", text: "oklch(0.45 0.11 55)" },
  email: {
    solid: "oklch(0.5 0.2 300)",
    tint: "oklch(0.955 0.03 300)",
    text: "oklch(0.44 0.19 300)",
  },
  watched: {
    solid: "oklch(0.66 0.11 175)",
    tint: "oklch(0.955 0.035 175)",
    text: "oklch(0.42 0.09 175)",
  },
  manual: { solid: "#8a8d98", tint: "#eeeef1", text: "#4a4d57" },
};
// The dark scheme is not designed yet: same hues, with the lightness of darkTones.
const darkSources: Sources = {
  api: { solid: "oklch(0.58 0.17 255)", tint: "oklch(0.3 0.05 255)", text: "oklch(0.85 0.08 255)" },
  rss: { solid: "oklch(0.74 0.15 62)", tint: "oklch(0.3 0.05 62)", text: "oklch(0.85 0.08 62)" },
  email: { solid: "oklch(0.5 0.2 300)", tint: "oklch(0.3 0.05 300)", text: "oklch(0.85 0.08 300)" },
  watched: {
    solid: "oklch(0.66 0.11 175)",
    tint: "oklch(0.3 0.05 175)",
    text: "oklch(0.85 0.08 175)",
  },
  manual: { solid: "#8a8d98", tint: "#24252b", text: "#b4b6c2" },
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
        primary: { main: "#111318", light: "#3d4049", dark: "#2a2d36", contrastText: "#ffffff" },
        secondary: { main: "#00897b" },
        background: { default: "#f7f7f8", paper: "#ffffff" },
        text: { primary: "#111318", secondary: "#60636e", disabled: "#a3a5b0" },
        divider: "#e6e6ea",
        action: { hover: "rgba(17,19,24,0.04)", selected: "rgba(17,19,24,0.07)" },
        tone: lightTones,
        source: lightSources,
        fill: "#efeff2",
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
        source: darkSources,
        fill: "#24252b",
      },
    },
  },
  typography: {
    fontFamily: sans,
    fontSize: 14,
    // Page headline, in-between heading and section title.
    h4: { fontWeight: 700, fontSize: "2.75rem", lineHeight: 1.05, letterSpacing: "-0.04em" },
    h5: { fontWeight: 600, fontSize: "1.5rem", lineHeight: 1.2, letterSpacing: "-0.03em" },
    h6: { fontWeight: 600, fontSize: "1.125rem", lineHeight: 1.35, letterSpacing: "-0.02em" },
    body1: { fontSize: "0.9375rem", lineHeight: 1.55, letterSpacing: 0 },
    body2: { fontSize: "0.875rem", lineHeight: 1.5, letterSpacing: 0 },
    button: { textTransform: "none", fontWeight: 500, letterSpacing: "0.005em" },
    caption: { letterSpacing: "0.01em" },
  },
  spacing: 8,
  shape: { borderRadius: 10 },
  components: {
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: { root: { borderRadius: 999, minHeight: 44 } },
    },
    MuiIconButton: { styleOverrides: { root: { borderRadius: 10 } } },
    MuiOutlinedInput: {
      styleOverrides: {
        root: ({ theme }) => ({ backgroundColor: theme.palette.background.paper }),
      },
    },
    MuiPaper: {
      styleOverrides: {
        rounded: { borderRadius: 16 },
        // Thin lines instead of shadows. Menus and dialogs float, so they keep theirs.
        elevation1: ({ theme }) => ({
          boxShadow: "none",
          border: `1px solid ${theme.palette.divider}`,
        }),
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
