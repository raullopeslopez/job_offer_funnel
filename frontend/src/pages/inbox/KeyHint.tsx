import { Box } from "@mui/material";
import { mono } from "../../theme";

// The key of a button in the action bar (specs/ui/inbox.feature). Hidden from the accessible
// name, which stays the button's text, and from a phone, which has no keyboard.
export function KeyHint({ children }: { children: string }) {
  return (
    <Box
      component="kbd"
      aria-hidden="true"
      sx={{
        display: { xs: "none", md: "inline-block" },
        ml: 1,
        px: 0.5,
        border: 1,
        borderColor: "divider",
        borderRadius: 0.5,
        fontFamily: mono,
        fontSize: "0.75rem",
        lineHeight: 1.4,
        opacity: 0.8,
      }}
    >
      {children}
    </Box>
  );
}
