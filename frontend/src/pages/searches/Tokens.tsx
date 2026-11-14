import { Box } from "@mui/material";
import { mono } from "../../theme";

// title: a tag with a border; keyword: a mono token; excluded: a mono token, struck through.
type Kind = "title" | "keyword" | "excluded";

type Props = { items: string[]; kind: Kind };

export function Tokens({ items, kind }: Props) {
  if (items.length === 0) return <Box sx={{ color: "text.disabled" }}>—</Box>;
  return (
    <Box sx={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
      {items.map((item) => (
        <Box
          key={item}
          component={kind === "excluded" ? "s" : "span"}
          sx={(theme) => {
            const palette = (theme.vars ?? theme).palette;
            const tone = palette.tone[kind === "excluded" ? "red" : "neutral"];
            return {
              display: "inline-flex",
              alignItems: "center",
              minHeight: 24,
              px: "8px",
              borderRadius: "7px",
              fontSize: 13,
              ...(kind === "title"
                ? { border: 1, borderColor: "divider", color: "text.primary" }
                : { fontFamily: mono, fontSize: 12, bgcolor: tone.bg, color: tone.fg }),
            };
          }}
        >
          {item}
        </Box>
      ))}
    </Box>
  );
}
