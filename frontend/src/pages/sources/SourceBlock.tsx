import { Box, Typography } from "@mui/material";
import type { ReactNode } from "react";
import { useId } from "react";
import { groupedPiecesSx } from "../../components/GroupedList";
import { sourceIcons } from "../../components/icons";
import { offerShape, type Source } from "../../theme";

type BlockProps = {
  kind: Source;
  title: string;
  text: string;
  // Shown instead of the list when the block has nothing.
  empty: ReactNode;
  children: ReactNode[];
};

// One way offers reach the inbox: its icon in the source's color, what the app does and
// what the user does, and the sources that arrive that way.
export function SourceBlock({ kind, title, text, empty, children }: BlockProps) {
  const Icon = sourceIcons[kind];
  const titleId = useId();
  return (
    <Box component="section" aria-labelledby={titleId}>
      <Box sx={{ display: "flex", gap: 2, alignItems: "flex-start", mb: 2 }}>
        <Box
          aria-hidden
          sx={{
            width: 40,
            height: 40,
            borderRadius: "12px",
            flexShrink: 0,
            display: "grid",
            placeItems: "center",
            bgcolor: `source.${kind}.solid`,
            color: "common.white",
          }}
        >
          <Icon aria-hidden sx={{ fontSize: 22 }} />
        </Box>
        <Box sx={{ minWidth: 0 }}>
          <Typography id={titleId} variant="h6" component="h2">
            {title}
          </Typography>
          <Typography variant="body2" sx={{ color: "text.secondary", maxWidth: 640 }}>
            {text}
          </Typography>
        </Box>
      </Box>
      {children.length > 0 ? (
        <Box component="ul" sx={{ ...groupedPiecesSx, listStyle: "none", m: 0, p: 0 }}>
          {children}
        </Box>
      ) : (
        <Box
          sx={{
            p: 2.5,
            border: 1,
            borderStyle: "dashed",
            borderColor: "divider",
            borderRadius: offerShape.groupRadius,
            color: "text.secondary",
            typography: "body2",
          }}
        >
          {empty}
        </Box>
      )}
    </Box>
  );
}

type ItemProps = { lead?: ReactNode; primary: string; secondary: ReactNode; actions: ReactNode };

// One source in a block: what it is, and its actions, always visible.
export function SourceItem({ lead, primary, secondary, actions }: ItemProps) {
  return (
    <Box
      component="li"
      sx={{
        display: "flex",
        alignItems: "center",
        flexWrap: "wrap",
        gap: 2,
        px: 2.5,
        py: 1.5,
        bgcolor: "background.paper",
        border: 1,
        borderColor: "divider",
      }}
    >
      {lead}
      <Box sx={{ flex: "1 1 240px", minWidth: 0 }}>
        <Typography sx={{ fontWeight: 600 }}>{primary}</Typography>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
            color: "text.secondary",
            typography: "body2",
            minWidth: 0,
          }}
        >
          {secondary}
        </Box>
      </Box>
      <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, ml: "auto" }}>{actions}</Box>
    </Box>
  );
}
