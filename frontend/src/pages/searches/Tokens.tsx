import { Box } from "@mui/material";
import { mono } from "../../theme";

type Props = { items: string[]; excluded?: boolean };

// Keywords as small mono tokens; the excluded ones are red and prefixed with a minus.
export function Tokens({ items, excluded }: Props) {
  if (items.length === 0) return <Box sx={{ color: "text.disabled" }}>—</Box>;
  const tone = excluded ? "red" : "neutral";
  return (
    <Box sx={{ display: "inline-flex", gap: "4px", overflow: "hidden" }}>
      {items.map((item) => (
        <Box
          key={item}
          component="span"
          sx={(theme) => ({
            display: "inline-flex",
            alignItems: "center",
            height: 20,
            px: "6px",
            borderRadius: "6px",
            fontFamily: mono,
            fontSize: 11.5,
            whiteSpace: "nowrap",
            bgcolor: (theme.vars ?? theme).palette.tone[tone].bg,
            color: (theme.vars ?? theme).palette.tone[tone].fg,
          })}
        >
          {excluded ? "−" : ""}
          {item}
        </Box>
      ))}
    </Box>
  );
}
