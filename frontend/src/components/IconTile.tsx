import type { SvgIconComponent } from "@mui/icons-material";
import { Box } from "@mui/material";
import type { Tone } from "../theme";

type Props = { icon: SvgIconComponent; size?: number; tone?: Tone };

// Decorative square with a tinted icon.
export function IconTile({ icon: Icon, size = 32, tone = "neutral" }: Props) {
  return (
    <Box
      aria-hidden
      sx={(theme) => ({
        width: size,
        height: size,
        borderRadius: "30%",
        flexShrink: 0,
        display: "grid",
        placeItems: "center",
        bgcolor: (theme.vars ?? theme).palette.tone[tone].bg,
        color: (theme.vars ?? theme).palette.tone[tone].fg,
      })}
    >
      <Icon aria-hidden sx={{ fontSize: Math.round(size * 0.56) }} />
    </Box>
  );
}
