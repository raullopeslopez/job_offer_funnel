import { Box, Chip } from "@mui/material";
import { toneOf } from "../theme";
import { offerStatusIcons, outcomeIcons, stageIcons } from "./icons";

const valueIcons = { ...stageIcons, ...outcomeIcons, ...offerStatusIcons };

type Props = {
  value: string | null | undefined;
  size?: "small" | "medium";
  icon?: boolean;
};

// Tinted pill for funnel values (stage, outcome, priority, offer status). Shows the raw value.
export function StatusChip({ value, size = "small", icon = true }: Props) {
  if (!value) {
    return (
      <Box component="span" sx={{ color: "text.disabled" }}>
        —
      </Box>
    );
  }
  const tone = toneOf[value] ?? "neutral";
  const Icon = icon ? valueIcons[value] : undefined;
  const small = size === "small";
  return (
    <Chip
      label={value}
      icon={
        Icon ? (
          <Icon aria-hidden sx={{ fontSize: `${small ? 14 : 16}px !important` }} />
        ) : (
          <Box
            component="span"
            data-slot="dot"
            sx={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              bgcolor: "currentColor",
              opacity: 0.85,
            }}
          />
        )
      }
      sx={(theme) => ({
        height: small ? 22 : 26,
        fontSize: small ? 12 : 13,
        bgcolor: (theme.vars ?? theme).palette.tone[tone].bg,
        color: (theme.vars ?? theme).palette.tone[tone].fg,
        letterSpacing: "0.01em",
        "& .MuiChip-icon": {
          color: "inherit",
          ml: Icon ? "6px" : "8px",
          mr: Icon ? "-4px" : "-2px",
        },
        "& .MuiChip-label": { px: small ? "8px" : "10px" },
      })}
    />
  );
}
