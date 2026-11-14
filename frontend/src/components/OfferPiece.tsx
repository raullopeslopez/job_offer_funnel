import { Box, Link, Typography } from "@mui/material";
import type { ReactNode } from "react";
import type { components } from "../api/schema";
import { mono, offerShape, type Source } from "../theme";
import { CountryTag } from "./CountryTag";
import { RelativeDate } from "./RelativeDate";
import { SourceTag } from "./SourceTag";

type Offer = Pick<
  components["schemas"]["OfferRead"],
  "title" | "url" | "company" | "created_at" | "job_board_name" | "location" | "countries"
>;

type Props = {
  offer: Offer;
  sourceKind: Source;
  actions?: ReactNode;
  strip?: ReactNode;
  footer?: ReactNode;
  /** Shown in place of the title's link, inside the same heading. */
  heading?: ReactNode;
  now?: Date;
};

// Its countries, or its location as published when it names no known country.
function countryLabels({ countries, location }: Offer): string[] {
  if (countries.length > 0) return countries;
  return location ? [location] : [];
}

// One offer: where it came from, company, country and age, the title as a link, and slots for its
// actions, its rule strip and a footer.
export function OfferPiece({ offer, sourceKind, actions, strip, footer, heading, now }: Props) {
  const sourceName = sourceKind === "watched" ? undefined : offer.job_board_name;
  return (
    <Box
      component="article"
      aria-label={offer.title}
      sx={{
        p: 2.5,
        bgcolor: "background.paper",
        border: 1,
        borderColor: "divider",
        borderRadius: offerShape.pieceRadius,
      }}
    >
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2 }}>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              flexWrap: "wrap",
              gap: 1.25,
              color: "text.secondary",
              typography: "body2",
            }}
          >
            <SourceTag kind={sourceKind} name={sourceName} />
            {countryLabels(offer).map((label) => (
              <CountryTag key={label} label={label} />
            ))}
            <span>
              {offer.company} ·{" "}
              <Box component="span" sx={{ fontFamily: mono }}>
                <RelativeDate value={offer.created_at} now={now} />
              </Box>
            </span>
          </Box>
          <Typography variant="h6" component="h3" sx={{ mt: 1 }}>
            {heading ?? (
              <Link href={offer.url} target="_blank" rel="noopener noreferrer" color="inherit">
                {offer.title}
              </Link>
            )}
          </Typography>
        </Box>
        {actions && <Box sx={{ display: "flex", gap: 1, flexShrink: 0 }}>{actions}</Box>}
      </Box>
      {strip && <Box sx={{ mt: 2 }}>{strip}</Box>}
      {footer && <Box sx={{ mt: 1.5 }}>{footer}</Box>}
    </Box>
  );
}
