import { Box, Link, Typography } from "@mui/material";
import type { ReactNode } from "react";
import type { components } from "../api/schema";
import { mono, type Source } from "../theme";
import { CompanyAvatar } from "./CompanyAvatar";
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
  /** What stands out about its state, after its country: "Near miss · filtered by one rule". */
  statusLine?: string;
  now?: Date;
  /** Hides its "Original posting" link, when the screen has its own. */
  hideOriginal?: boolean;
};

// Its countries, or its location as published when it names no known country.
function countryLabels({ countries, location }: Offer): string[] {
  if (countries.length > 0) return countries;
  return location ? [location] : [];
}

/** How many countries an offer has besides the one shown: "+1 country", "+27 countries". */
export function moreCountries(count: number): string {
  return count === 1 ? "+1 country" : `+${count} countries`;
}

/** Where the job is, in one line: its first country, and how many more it has. */
export function whereText(offer: Offer): string {
  const [first, ...rest] = countryLabels(offer);
  if (!first) return "";
  return rest.length > 0 ? `${first} ${moreCountries(rest.length)}` : first;
}

// One offer, as the reading pane shows it, with no box around it: where it came from, its age,
// the company, the title, the country and a status line, and slots for its actions, its rule strip and a
// footer. On a phone the actions go full width at its foot, after the rest.
export function OfferPiece({
  offer,
  sourceKind,
  actions,
  strip,
  footer,
  statusLine,
  now,
  hideOriginal,
}: Props) {
  const sourceName = sourceKind === "watched" ? undefined : offer.job_board_name;
  const [country, ...otherCountries] = countryLabels(offer);
  return (
    <Box
      component="article"
      aria-label={offer.title}
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "minmax(0, 1fr)", sm: "minmax(0, 1fr) auto" },
        gridTemplateAreas: {
          xs: '"main" "strip" "footer" "actions"',
          sm: '"main actions" "strip strip" "footer footer"',
        },
        columnGap: 2,
        rowGap: 0,
      }}
    >
      <Box sx={{ gridArea: "main", minWidth: 0 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <CompanyAvatar name={offer.company} />
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="subtitle2" component="span" sx={{ display: "block" }}>
              {offer.company}
            </Typography>
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
              <Box component="span" sx={{ fontFamily: mono }}>
                <RelativeDate value={offer.created_at} now={now} />
              </Box>
            </Box>
          </Box>
          {!hideOriginal && (
            <Link
              href={offer.url}
              target="_blank"
              rel="noopener noreferrer"
              variant="body2"
              sx={{ ml: "auto", whiteSpace: "nowrap" }}
            >
              Original posting
            </Link>
          )}
        </Box>
        <Typography variant="h4" component="h3" sx={{ mt: 3 }}>
          {offer.title}
        </Typography>
        <Box
          sx={{
            mt: 1.5,
            display: "flex",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 1,
            color: "text.secondary",
            typography: "body2",
          }}
        >
          {country && <CountryTag label={country} />}
          {otherCountries.length > 0 && (
            <Box
              component="span"
              title={otherCountries.join(", ")}
              sx={{ color: "text.secondary" }}
            >
              {moreCountries(otherCountries.length)}
            </Box>
          )}
          {statusLine && (
            <>
              {country && <span aria-hidden>·</span>}
              <span>{statusLine}</span>
            </>
          )}
        </Box>
      </Box>
      {actions && (
        <Box
          sx={{
            gridArea: "actions",
            mt: { xs: 2, sm: 0 },
            alignSelf: "start",
            display: "grid",
            gridAutoFlow: "column",
            gridAutoColumns: { xs: "minmax(0, 1fr)", sm: "auto" },
            gap: 1,
            "& .MuiButton-root": { minHeight: { xs: 44, sm: "auto" } },
          }}
        >
          {actions}
        </Box>
      )}
      {strip && <Box sx={{ gridArea: "strip" }}>{strip}</Box>}
      {footer && <Box sx={{ gridArea: "footer", mt: 1.5 }}>{footer}</Box>}
    </Box>
  );
}
