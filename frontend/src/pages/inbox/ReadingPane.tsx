import { Box, Link } from "@mui/material";
import type { ReactNode } from "react";
import { OfferPiece } from "../../components/OfferPiece";
import { offerSourceKind } from "../../components/offerSource";
import { ActionBar } from "./ActionBar";
import { discardReasonText } from "./discardReasons";
import type { NearMissActions } from "./MaybeGroup";
import type { OfferActions, OfferContext } from "./OfferList";
import { OfferStrip } from "./OfferStrip";
import { TriagePending, TriageVerdict } from "./TriageVerdict";
import type { Offer } from "./types";
import { moreVariantsOfRole } from "./variants";

/** One offer of the inbox as the pane shows it, with its strip and the actions given. */
export function InboxOffer({
  offer,
  jobBoards,
  profiles,
  now = new Date(),
  extra,
  triageRunning,
}: OfferContext & {
  offer: Offer;
  /** Shown under its company and country: the variants of its role. */
  extra?: ReactNode;
}) {
  const sourceKind = offerSourceKind(offer, jobBoards);
  const waiting =
    triageRunning &&
    offer.status === "pending" &&
    offer.filter_reason?.has_description &&
    (!offer.filtered || offer.filter_reason.near_miss);
  const verdict =
    (offer.status === "pending" && offer.triage && <TriageVerdict offer={offer} />) ||
    (waiting && <TriagePending />);
  return (
    <OfferPiece
      offer={offer}
      sourceKind={sourceKind}
      now={now}
      statusLine={statusLine(offer)}
      strip={
        <>
          {extra}
          {verdict}
          <OfferStrip offer={offer} sourceKind={sourceKind} profiles={profiles} />
        </>
      }
    />
  );
}

// What stands out about the state of an offer, under its title.
function statusLine(offer: Offer): string | undefined {
  if (offer.status === "discarded") return discardReasonText(offer);
  if (offer.filtered && offer.filter_reason?.near_miss) return "Near miss · filtered by one rule";
  return undefined;
}

/** A near miss: a filtered offer that fails a single rule (specs/inbox/rescues.feature). */
const isNearMiss = (offer: Offer) => offer.filtered && offer.filter_reason?.near_miss === true;

type Props = OfferContext &
  Omit<OfferActions, "onDiscard"> &
  NearMissActions & {
    offer: Offer | null;
    /** Which offer of the view it is, for the action bar. */
    position?: { index: number; total: number };
    onDiscarded: (offer: Offer) => void;
    /** The other variants of its role, when it is the first of them. */
    variants?: { count: number; open: boolean; onToggle: () => void };
  };

// The reading pane (specs/ui/inbox.feature): the offer chosen in the list, with its strip and
// its verdict, and the action bar at its foot. Empty while no offer is chosen.
export function ReadingPane({
  offer,
  position,
  onDiscarded,
  variants,
  onPromote,
  onRestore,
  onRightlyFiltered,
  ...context
}: Props) {
  if (!offer) return null;
  const nearMiss = isNearMiss(offer);
  return (
    <Box key={offer.id} sx={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
      <InboxOffer offer={offer} {...context} extra={variants && <VariantsToggle {...variants} />} />
      <ActionBar
        offer={offer}
        position={position}
        nearMiss={nearMiss}
        profiles={context.profiles}
        onDiscarded={onDiscarded}
        onPromote={onPromote}
        onRestore={onRestore}
        onRightlyFiltered={onRightlyFiltered}
      />
    </Box>
  );
}

// Opens the other variants of its role in the list, under its row.
function VariantsToggle({ count, open, onToggle }: NonNullable<Props["variants"]>) {
  return (
    <Box sx={{ mb: 2 }}>
      <Link component="button" type="button" aria-expanded={open} onClick={onToggle}>
        {moreVariantsOfRole(count)}
      </Link>
    </Box>
  );
}
