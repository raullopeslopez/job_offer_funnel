import { Box } from "@mui/material";

type Props = {
  label: string;
  count: number;
};

// Tab text with a neutral count pill, for `<Tab label={<TabLabel … />} />`.
export function TabLabel({ label, count }: Props) {
  return (
    <Box component="span" sx={{ display: "inline-flex", alignItems: "center", gap: 1 }}>
      {label}
      <Box
        component="span"
        sx={(theme) => ({
          display: "inline-grid",
          placeItems: "center",
          boxSizing: "border-box",
          minWidth: 20,
          height: 20,
          px: "6px",
          borderRadius: 999,
          fontSize: 11.5,
          fontVariantNumeric: "tabular-nums",
          bgcolor: (theme.vars ?? theme).palette.tone.neutral.bg,
          color: (theme.vars ?? theme).palette.tone.neutral.fg,
        })}
      >
        {count}
      </Box>
    </Box>
  );
}
