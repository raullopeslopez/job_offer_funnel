import { Box } from "@mui/material";
import type { ReactNode } from "react";
import { offerShape, offerType } from "../theme";

// The rules of a profile side by side, in equal columns.
export function RuleStrip({ children }: { children: ReactNode }) {
  return (
    <Box
      role="group"
      aria-label="Rules"
      sx={{
        display: "grid",
        gridAutoFlow: "column",
        gridAutoColumns: "minmax(0, 1fr)",
        gap: offerShape.ruleGap,
      }}
    >
      {children}
    </Box>
  );
}

type MergedProps = { span: number; children: ReactNode };

// Several rules that cannot be told apart (no description to read), as one dashed cell.
export function MergedRuleCell({ span, children }: MergedProps) {
  return (
    <Box
      data-state="unknown"
      sx={{
        gridColumn: `span ${span}`,
        display: "flex",
        alignItems: "center",
        px: 1.25,
        py: 0.75,
        borderRadius: offerShape.pieceRadius,
        border: "1px dashed",
        borderColor: "text.disabled",
        color: "text.secondary",
        ...offerType.cellValue,
      }}
    >
      {children}
    </Box>
  );
}
