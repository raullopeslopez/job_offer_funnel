import { Box, Typography } from "@mui/material";
import type { ReactNode } from "react";
import { offerType } from "../theme";

// The rules of a profile as a definition list under a "Rules" heading: a line per rule, so no
// value is cut on a phone.
export function RuleStrip({ children }: { children: ReactNode }) {
  return (
    <Box component="section" sx={{ mt: 4 }}>
      <Typography component="h4" sx={{ ...offerType.cellLabel, color: "text.secondary" }}>
        Rules
      </Typography>
      <Box component="dl" sx={{ m: 0, mt: 1, borderTop: 1, borderColor: "divider" }}>
        {children}
      </Box>
    </Box>
  );
}

// Several rules that cannot be told apart (no description to read), as one line that says why.
export function MergedRuleCell({ children }: { children: ReactNode }) {
  return (
    <Box
      data-state="unknown"
      sx={{ py: 1.25, borderBottom: 1, borderColor: "divider", color: "text.secondary" }}
    >
      <Box component="dd" sx={{ m: 0, ...offerType.cellValue }}>
        {children}
      </Box>
    </Box>
  );
}
