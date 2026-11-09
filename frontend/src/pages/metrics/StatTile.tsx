import type { SvgIconComponent } from "@mui/icons-material";
import { Paper, Stack, Typography } from "@mui/material";
import { IconTile } from "../../components/IconTile";
import { mono, type Tone } from "../../theme";

type Props = {
  icon: SvgIconComponent;
  tone: Tone;
  label: string;
  value: string | number;
  hint?: string;
};

/** A key figure: tinted icon and label on top, the value in mono below and an optional hint. */
export function StatTile({ icon, tone, label, value, hint }: Props) {
  return (
    <Paper sx={{ p: "16px", display: "grid", gap: "10px", minWidth: 0 }}>
      <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
        <IconTile icon={icon} size={28} tone={tone} />
        <Typography variant="body2" color="text.secondary">
          {label}
        </Typography>
      </Stack>
      <Typography
        component="div"
        sx={{
          fontFamily: mono,
          fontSize: "1.75rem",
          fontWeight: 500,
          lineHeight: 1.1,
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {value}
      </Typography>
      {hint && (
        <Typography variant="caption" color="text.secondary">
          {hint}
        </Typography>
      )}
    </Paper>
  );
}
