import type { SvgIconComponent } from "@mui/icons-material";
import { Box, Typography } from "@mui/material";

type Props = {
  icon: SvgIconComponent;
  title: string;
  text?: string;
};

// Centered empty state, meant for the DataGrid `slots={{ noRowsOverlay }}`.
export function EmptyState({ icon: Icon, title, text }: Props) {
  return (
    <Box
      sx={{
        display: "grid",
        justifyItems: "center",
        alignContent: "center",
        gap: "6px",
        textAlign: "center",
        py: 2,
        height: "100%",
      }}
    >
      <Box
        aria-hidden
        sx={(theme) => ({
          width: 48,
          height: 48,
          borderRadius: "14px",
          display: "grid",
          placeItems: "center",
          mb: "6px",
          bgcolor: (theme.vars ?? theme).palette.tone.neutral.bg,
          color: (theme.vars ?? theme).palette.text.secondary,
        })}
      >
        <Icon aria-hidden sx={{ fontSize: 24 }} />
      </Box>
      <Typography sx={{ fontWeight: 500 }}>{title}</Typography>
      {text && (
        <Typography variant="body2" sx={{ color: "text.secondary", maxWidth: 320 }}>
          {text}
        </Typography>
      )}
    </Box>
  );
}
