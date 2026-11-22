import { Box, Typography } from "@mui/material";
import type { ReactNode } from "react";
import { mono, offerShape } from "../theme";

type Props = {
  title: string;
  count: number;
  /** In place of "{title} · {count} offers". */
  heading?: ReactNode;
  note?: ReactNode;
  children: ReactNode;
};

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

// A titled group of rows: its title and count, an optional note, and its rows as a list split
// by thin lines, with no box around them.
export function GroupedList({ title, count, heading, note, children }: Props) {
  return (
    <Box component="section" aria-label={title}>
      <GroupHeader title={title} count={count} heading={heading} note={note} />
      <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>
        {children}
      </Box>
    </Box>
  );
}

/** The title of a group of rows, "{title} · {count} offers", and its note. */
export function GroupHeader({ title, count, heading, note }: Omit<Props, "children">) {
  return (
    <Box sx={{ px: 2, pt: 2.5, pb: 1, borderBottom: 1, borderColor: "divider" }}>
      <Typography
        variant="overline"
        component="h2"
        sx={{ display: "block", lineHeight: 1.6, color: "text.secondary" }}
      >
        {heading ?? (
          <>
            {title} · <Count value={count} /> {count === 1 ? "offer" : "offers"}
          </>
        )}
      </Typography>
      {note && (
        <Typography variant="body2" color="text.secondary">
          {note}
        </Typography>
      )}
    </Box>
  );
}

/** A number in a heading, in the monospaced type. */
export function Count({ value }: { value: number }) {
  return (
    <Box component="span" sx={{ fontFamily: mono, fontWeight: 500 }}>
      {value}
    </Box>
  );
}
