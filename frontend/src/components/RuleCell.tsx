import { Box } from "@mui/material";
import { offerType } from "../theme";

export type RuleState = "pass" | "unknown" | "failed";

type Props = {
  label: string;
  value?: string | null;
  state: RuleState;
  /** The literal sentence of the description behind a failed rule, shown under its value. */
  evidence?: string | null;
};

// The dot says the state by shape, not only by color: filled (pass), hollow (unknown), red and
// filled (failed, which also says "filtered it").
function StateDot({ state }: { state: RuleState }) {
  const color = state === "failed" ? "tone.red.fg" : state === "unknown" ? "text.disabled" : "text.primary";
  return (
    <Box
      aria-hidden
      data-dot={state === "unknown" ? "hollow" : "filled"}
      sx={{
        flexShrink: 0,
        width: 8,
        height: 8,
        borderRadius: "50%",
        border: "1.5px solid",
        borderColor: color,
        bgcolor: state === "unknown" ? "transparent" : color,
      }}
    />
  );
}

// One rule of the profile and what the offer gave for it, as a term and its definition in the
// list of rules. The value wraps instead of being cut.
export function RuleCell({ label, value, state, evidence }: Props) {
  return (
    <Box
      data-state={state}
      sx={{
        display: "grid",
        gridTemplateColumns: "112px minmax(0, 1fr)",
        columnGap: 1,
        py: 1.25,
        borderBottom: 1,
        borderColor: "divider",
      }}
    >
      <Box
        component="dt"
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1,
          ...offerType.cellValue,
          color: "text.secondary",
        }}
      >
        <StateDot state={state} />
        {label}
      </Box>
      <Box component="dd" sx={{ m: 0, minWidth: 0, overflowWrap: "anywhere" }}>
        <Box
          sx={{
            ...offerType.cellValue,
            fontWeight: state === "unknown" ? 400 : 600,
            color: state === "unknown" ? "text.secondary" : "text.primary",
          }}
        >
          {state === "unknown" ? "Not stated" : value || "—"}
          {state === "failed" && (
            <Box
              component="span"
              sx={{ ml: 1, fontSize: "0.75rem", fontWeight: 500, color: "tone.red.fg" }}
            >
              filtered it
            </Box>
          )}
        </Box>
        {evidence && (
          <Box sx={{ mt: 0.5, fontSize: "0.9rem", color: "text.secondary" }}>“{evidence}”</Box>
        )}
      </Box>
    </Box>
  );
}
