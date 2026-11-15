import ChevronRightOutlined from "@mui/icons-material/ChevronRightOutlined";
import { Box, ButtonBase, Typography } from "@mui/material";
import { type ReactNode, useState } from "react";
import { groupedPiecesSx } from "../../components/GroupedList";
import { mono } from "../../theme";
import type { Offer } from "./types";

type Variant = Pick<Offer, "company" | "base_title">;

const variantKey = (offer: Variant) => `${offer.company}|${offer.base_title}`.toLowerCase();

/** The offers split into runs of variants of the same role, in the same order. */
export function groupVariants<T extends Variant>(offers: T[]) {
  const runs: { first: T; offers: T[] }[] = [];
  for (const offer of offers) {
    const last = runs.at(-1);
    if (last && variantKey(last.first) === variantKey(offer)) last.offers.push(offer);
    else runs.push({ first: offer, offers: [offer] });
  }
  return runs;
}

type Props = { company: string; baseTitle: string; count: number; children: ReactNode };

// The variants of a role as one closed group that opens to show its pieces
// (specs/ui/inbox.feature).
export function VariantGroup({ company, baseTitle, count, children }: Props) {
  const [open, setOpen] = useState(false);
  return (
    <Box
      component="section"
      aria-label={`${company} · ${baseTitle} · ${count} variants`}
      sx={{ bgcolor: "background.paper", border: 1, borderColor: "divider" }}
    >
      <ButtonBase
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        sx={{ width: 1, p: 2, gap: 1, justifyContent: "space-between", textAlign: "left" }}
      >
        <Typography variant="subtitle1" component="h3" sx={{ fontWeight: 600, minWidth: 0 }}>
          {company} · {baseTitle} ·{" "}
          <Box component="span" sx={{ fontFamily: mono, fontWeight: 500 }}>
            {count}
          </Box>{" "}
          variants
        </Typography>
        <ChevronRightOutlined
          aria-hidden
          sx={{ color: "text.secondary", transform: open ? "rotate(90deg)" : "none" }}
        />
      </ButtonBase>
      {open && <Box sx={{ ...groupedPiecesSx, px: 1, pb: 1 }}>{children}</Box>}
    </Box>
  );
}
