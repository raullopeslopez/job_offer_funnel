import { Box, Tooltip } from "@mui/material";
import { formatDate } from "../pages/applications/options";

const DAY_MS = 86_400_000;

export function relativeLabel(value: string, now: Date): string {
  const today = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
  const days = Math.round((today - new Date(value).getTime()) / DAY_MS);
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 7) return `${days}d ago`;
  if (days < 35) return `${Math.round(days / 7)}w ago`;
  return formatDate(value);
}

type Props = { value: string | null | undefined; now?: Date };

// Relative date ("3d ago") with the full date in a tooltip.
export function RelativeDate({ value, now = new Date() }: Props) {
  if (!value) {
    return (
      <Box component="span" sx={{ color: "text.disabled" }}>
        {"—"}
      </Box>
    );
  }
  return (
    <Tooltip title={formatDate(value)}>
      <Box
        component="time"
        dateTime={new Date(value).toISOString().slice(0, 10)}
        sx={{ color: "text.secondary", fontVariantNumeric: "tabular-nums" }}
      >
        {relativeLabel(value, now)}
      </Box>
    </Tooltip>
  );
}
