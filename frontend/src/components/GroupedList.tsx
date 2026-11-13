import { Box, Typography } from "@mui/material";
import type { ReactNode } from "react";
import { mono, offerShape } from "../theme";

type Props = { title: string; count: number; children: ReactNode };

const r = offerShape.groupRadius;

// A column of pieces 3px apart, round at the ends of the group and tighter between.
export const groupedPiecesSx = {
  display: "flex",
  flexDirection: "column",
  gap: offerShape.pieceGap,
  "& > *": { borderRadius: offerShape.pieceRadius },
  "& > :first-of-type": { borderTopLeftRadius: r, borderTopRightRadius: r },
  "& > :last-of-type": { borderBottomLeftRadius: r, borderBottomRightRadius: r },
} as const;

// A titled group of pieces: 3px apart, round at the ends of the group and tighter between.
export function GroupedList({ title, count, children }: Props) {
  return (
    <Box component="section" aria-label={title}>
      <Typography variant="h6" component="h2" sx={{ mb: 1.5 }}>
        {title} ·{" "}
        <Box component="span" sx={{ fontFamily: mono, fontWeight: 500 }}>
          {count}
        </Box>{" "}
        {count === 1 ? "offer" : "offers"}
      </Typography>
      <Box sx={groupedPiecesSx}>{children}</Box>
    </Box>
  );
}
