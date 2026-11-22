import { Box, Button, Link, Typography } from "@mui/material";
import type { ReactNode } from "react";
import { Link as RouterLink } from "react-router";
import { OfferPiece } from "../../components/OfferPiece";
import { offerSourceKind } from "../../components/offerSource";
import { DiscardingOffer } from "./DiscardingOffer";
import { discardReasonText } from "./discardReasons";
import { type NearMissActions, NearMissButtons } from "./MaybeGroup";
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
  actions,
  extra,
  triageRunning,
  onDiscarded,
}: OfferContext & {
  offer: Offer;
  actions: ReactNode;
  /** Shown under its company and country: the variants of its role. */
  extra?: ReactNode;
  /** Given, a pending offer with a suggested discard can be discarded as suggested. */
  onDiscarded?: (offer: Offer) => void;
}) {
  const sourceKind = offerSourceKind(offer, jobBoards);
  const waiting =
    triageRunning &&
    offer.status === "pending" &&
    offer.filter_reason?.has_description &&
    (!offer.filtered || offer.filter_reason.near_miss);
  return (
    <OfferPiece
      offer={offer}
      sourceKind={sourceKind}
      now={now}
      actions={actions}
      strip={
        <>
          {extra}
          <OfferStrip offer={offer} sourceKind={sourceKind} profiles={profiles} />
        </>
      }
      footer={
        (offer.status === "discarded" && (
          <Typography variant="body2" color="text.secondary">
            Reason: {discardReasonText(offer)}
          </Typography>
        )) ||
        (offer.status === "pending" && offer.triage && (
          <TriageVerdict offer={offer} onDiscarded={onDiscarded} />
        )) ||
        (waiting && <TriagePending />)
      }
    />
  );
}

/** A near miss: a filtered offer that fails a single rule (specs/inbox/rescues.feature). */
const isNearMiss = (offer: Offer) => offer.filtered && offer.filter_reason?.near_miss === true;

type Props = OfferContext &
  OfferActions &
  NearMissActions & {
    offer: Offer | null;
    /** The offer open to discard, if any. */
    discardingId?: string | null;
    onCancelDiscard: () => void;
    onDiscarded: (offer: Offer) => void;
    /** The other variants of its role, when it is the first of them. */
    variants?: { count: number; open: boolean; onToggle: () => void };
  };

// The reading pane (specs/ui/inbox.feature): the offer chosen in the list, with its strip, its
// verdict and what can be done with it. Empty while no offer is chosen.
export function ReadingPane({
  offer,
  discardingId,
  onCancelDiscard,
  onDiscarded,
  variants,
  onDiscard,
  onPromote,
  onRestore,
  onRightlyFiltered,
  ...context
}: Props) {
  if (!offer) return null;
  if (offer.id === discardingId) {
    return (
      <DiscardingOffer
        key={offer.id}
        offer={offer}
        {...context}
        onCancel={onCancelDiscard}
        onDiscarded={onDiscarded}
      />
    );
  }
  const nearMiss = isNearMiss(offer);
  return (
    <InboxOffer
      key={offer.id}
      offer={offer}
      {...context}
      extra={variants && <VariantsToggle {...variants} />}
      actions={
        nearMiss ? (
          <NearMissButtons
            offer={offer}
            onPromote={onPromote}
            onRightlyFiltered={onRightlyFiltered}
          />
        ) : (
          <Actions
            offer={offer}
            onDiscard={onDiscard}
            onPromote={onPromote}
            onRestore={onRestore}
          />
        )
      }
      onDiscarded={nearMiss ? undefined : onDiscarded}
    />
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

function Actions({ offer, onDiscard, onPromote, onRestore }: { offer: Offer } & OfferActions) {
  if (offer.status === "pending") {
    return (
      <>
        <Button variant="contained" onClick={() => onPromote(offer)}>
          Promote
        </Button>
        <Button variant="outlined" onClick={() => onDiscard(offer)}>
          Discard
        </Button>
      </>
    );
  }
  if (offer.status === "discarded") {
    return (
      <Button variant="outlined" onClick={() => onRestore(offer)}>
        Restore
      </Button>
    );
  }
  if (offer.application_id) {
    return (
      <Link component={RouterLink} to={`/applications/${offer.application_id}`}>
        View application
      </Link>
    );
  }
  return null;
}
