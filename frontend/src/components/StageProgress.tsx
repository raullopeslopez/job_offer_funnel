import { Box, Tooltip } from "@mui/material";
import { STAGES } from "../pages/applications/options";

type Props = {
  stage: string;
  outcome?: string | null;
  size?: "small" | "large";
};

// Segmented bar: how far along the funnel. Greyed when the application is closed.
export function StageProgress({ stage, outcome, size = "small" }: Props) {
  const current = STAGES.indexOf(stage as (typeof STAGES)[number]);
  const large = size === "large";
  const label = `Stage ${current + 1} of ${STAGES.length}${outcome ? ", closed" : ""}`;
  return (
    <Tooltip title={outcome ? `${stage} · ${outcome}` : stage}>
      <Box
        component="span"
        role="img"
        aria-label={label}
        sx={{ display: "inline-flex", gap: "3px" }}
      >
        {STAGES.map((s, i) => (
          <Box
            key={s}
            component="span"
            sx={{
              width: large ? { xs: 28, md: 40 } : 14,
              height: large ? 6 : 4,
              borderRadius: large ? "6px" : "4px",
              bgcolor: i <= current ? (outcome ? "text.disabled" : "primary.main") : "divider",
            }}
          />
        ))}
      </Box>
    </Tooltip>
  );
}
