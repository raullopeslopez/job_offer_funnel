import { Box, ButtonBase, Typography } from "@mui/material";
import { CompanyAvatar } from "../../components/CompanyAvatar";
import { whereText } from "../../components/OfferPiece";
import { RelativeDate } from "../../components/RelativeDate";
import { SourceTag } from "../../components/SourceTag";
import type { Source } from "../../theme";
import { mono, offerShape, offerType } from "../../theme";
import type { SearchProfile } from "./filterRules";
import { rowLine } from "./rowLine";
import type { Offer } from "./types";

type Props = {
  offer: Offer;
  sourceKind: Source;
  selected: boolean;
  /** The profiles, to say which rule filtered a filtered offer. */
  profiles?: SearchProfile[];
  onSelect: (offer: Offer) => void;
  /** How many more variants of its role it stands for, while they are closed. */
  variants?: number;
  /** Set off from the row before it: a variant shown under the first of its role. */
  indented?: boolean;
  now?: Date;
};

/** "+1 variant", "+2 variants". */
export function moreVariants(count: number): string {
  return count === 1 ? "+1 variant" : `+${count} variants`;
}

// One offer in the list, in one row (specs/ui/inbox.feature): its title, its company and where
// it is, its age and its source. The title is the button that opens it in the reading pane,
// and the whole row answers to it. The selected row has a tinted background and an ink line
// on its left.
export function OfferRow({
  offer,
  sourceKind,
  selected,
  profiles = [],
  onSelect,
  variants = 0,
  indented = false,
  now,
}: Props) {
  const where = whereText(offer);
  const { label, tone, line } = rowLine(offer, sourceKind, profiles);
  return (
    <Box
      component="li"
      sx={{
        position: "relative",
        display: "grid",
        gridTemplateColumns: "auto minmax(0, 1fr) auto",
        columnGap: 1.5,
        py: 1.5,
        pl: indented ? 4 : 2,
        pr: 2,
        borderBottom: 1,
        borderColor: "divider",
        bgcolor: selected ? "rowSelected" : undefined,
        boxShadow: selected
          ? (theme) => `inset 2px 0 0 ${(theme.vars ?? theme).palette.text.primary}`
          : undefined,
        "&:hover": selected ? undefined : { bgcolor: "action.hover" },
        "&:has(:focus-visible)": { outline: 2, outlineColor: "text.primary", outlineOffset: -2 },
      }}
    >
      <Box sx={{ mt: 0.25 }}>
        <CompanyAvatar name={offer.company} size={28} />
      </Box>
      <Box sx={{ minWidth: 0 }}>
        <ButtonBase
          aria-current={selected ? "true" : undefined}
          onClick={() => onSelect(offer)}
          disableRipple
          sx={{
            display: "block",
            maxWidth: 1,
            textAlign: "left",
            typography: "body1",
            fontWeight: 500,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
            // The whole row opens the offer, not only its title.
            "&::after": { content: '""', position: "absolute", inset: 0 },
            "&:focus-visible": { outline: "none" },
          }}
        >
          {offer.title}
        </ButtonBase>
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ mt: 0.25, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}
        >
          {[offer.company, where, variants > 0 ? moreVariants(variants) : ""]
            .filter(Boolean)
            .join(" · ")}
        </Typography>
        <Box sx={{ mt: 0.5, display: "flex", alignItems: "center", gap: 1, minWidth: 0 }}>
          <Box
            component="span"
            sx={{
              flexShrink: 0,
              display: "inline-flex",
              alignItems: "center",
              height: 20,
              px: 0.75,
              borderRadius: offerShape.tagRadius,
              bgcolor: `tone.${tone}.bg`,
              color: `tone.${tone}.fg`,
              ...offerType.tag,
              fontWeight: 600,
              whiteSpace: "nowrap",
            }}
          >
            {label}
          </Box>
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}
          >
            {line}
          </Typography>
        </Box>
      </Box>
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-end",
          gap: 0.5,
          color: "text.secondary",
          typography: "body2",
        }}
      >
        <Box component="span" sx={{ fontFamily: mono, whiteSpace: "nowrap" }}>
          <RelativeDate value={offer.created_at} now={now} />
        </Box>
        <SourceTag
          kind={sourceKind}
          name={sourceKind === "watched" ? undefined : offer.job_board_name}
        />
      </Box>
    </Box>
  );
}
