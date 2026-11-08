import { createTheme } from "@mui/material/styles";

// The only place for color, typography, spacing and shape.
export const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#3949ab" },
    secondary: { main: "#00897b" },
    background: { default: "#f5f6fa" },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
  },
  spacing: 8,
  shape: { borderRadius: 8 },
});
