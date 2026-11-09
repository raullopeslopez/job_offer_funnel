import { Box } from "@mui/material";

type Props = {
  value: string | null | undefined;
  showLabel?: boolean;
};

const FILLED: Record<string, number> = { high: 3, medium: 2, low: 1 };
const HEIGHTS = [6, 9, 12];

// Three ascending bars filled by priority, with the raw value beside them.
export function PriorityBars({ value, showLabel = true }: Props) {
  if (!value) {
    return (
      <Box component="span" sx={{ color: "text.disabled" }}>
        —
      </Box>
    );
  }
  const filled = FILLED[value] ?? 0;
  return (
    <Box component="span" sx={{ display: "inline-flex", alignItems: "center", gap: 1 }}>
      <Box
        component="span"
        role="img"
        aria-label={`Priority ${value}`}
        sx={{ display: "inline-flex", alignItems: "flex-end", gap: "2px", height: 12 }}
      >
        {HEIGHTS.map((height, i) => (
          <Box
            key={height}
            component="span"
            sx={(theme) => {
              const palette = (theme.vars ?? theme).palette;
              const color =
                value === "high"
                  ? palette.tone.red.fg
                  : value === "medium"
                    ? palette.tone.amber.fg
                    : palette.text.secondary;
              return {
                width: 3,
                height,
                borderRadius: "1px",
                bgcolor: i < filled ? color : palette.divider,
              };
            }}
          />
        ))}
      </Box>
      {showLabel && (
        <Box component="span" sx={{ color: "text.secondary", typography: "caption" }}>
          {value}
        </Box>
      )}
    </Box>
  );
}
