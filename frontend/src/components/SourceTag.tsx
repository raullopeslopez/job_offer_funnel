import { Box } from "@mui/material";
import { offerShape, offerType, type Source } from "../theme";
import { sourceIcons } from "./icons";

const prefixes: Record<Source, string> = {
  api: "API",
  rss: "RSS",
  email: "Email",
  watched: "Watched company",
  manual: "By hand",
};

export function sourceLabel(kind: Source, name?: string | null): string {
  if (kind === "watched" || !name) return prefixes[kind];
  return `${prefixes[kind]} · ${name}`;
}

type Props = { kind: Source; name?: string | null };

// Where an offer came from: the source's color, always with its icon and label.
export function SourceTag({ kind, name }: Props) {
  const Icon = sourceIcons[kind];
  return (
    <Box
      component="span"
      sx={{
        display: "inline-flex",
        alignItems: "center",
        gap: 0.75,
        height: offerShape.tagHeight,
        px: 1.25,
        borderRadius: offerShape.tagRadius,
        bgcolor: `source.${kind}.tint`,
        color: `source.${kind}.text`,
        whiteSpace: "nowrap",
        ...offerType.tag,
      }}
    >
      <Icon aria-hidden sx={{ fontSize: offerShape.iconSize }} />
      {sourceLabel(kind, name)}
    </Box>
  );
}
