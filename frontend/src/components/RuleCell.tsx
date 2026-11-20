import { Box } from "@mui/material";
import { offerShape, offerType } from "../theme";

export type RuleState = "pass" | "unknown" | "failed";

type Props = { label: string; value?: string | null; state: RuleState };

// One rule of the profile and what the offer gave for it. The three states differ by
// shape, not only by color: filled (pass), dashed border (unknown), ink with a suffix (failed).
// On a phone the value wraps instead of being cut.
export function RuleCell({ label, value, state }: Props) {
  return (
    <Box
      data-state={state}
      sx={{
        minWidth: 0,
        px: 1.25,
        py: 0.75,
        borderRadius: offerShape.pieceRadius,
        border: "1px solid transparent",
        ...(state === "pass" && { bgcolor: "fill" }),
        ...(state === "unknown" && { borderStyle: "dashed", borderColor: "text.disabled" }),
        ...(state === "failed" && { bgcolor: "primary.main", color: "primary.contrastText" }),
      }}
    >
      <Box
        sx={{
          ...offerType.cellLabel,
          color: state === "failed" ? "inherit" : "text.secondary",
        }}
      >
        {state === "failed" ? `${label} · filtered it` : label}
      </Box>
      <Box
        sx={{
          ...offerType.cellValue,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: { xs: "normal", sm: "nowrap" },
          overflowWrap: "anywhere",
          fontWeight: state === "unknown" ? 400 : 600,
          color: state === "unknown" ? "text.secondary" : "inherit",
        }}
      >
        {state === "unknown" ? "Not stated" : value || "—"}
      </Box>
    </Box>
  );
}
