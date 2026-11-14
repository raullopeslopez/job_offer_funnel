import type { SvgIconComponent } from "@mui/icons-material";
import ArrowUpwardOutlined from "@mui/icons-material/ArrowUpwardOutlined";
import DeleteOutlineOutlined from "@mui/icons-material/DeleteOutlineOutlined";
import FilterAltOutlined from "@mui/icons-material/FilterAltOutlined";
import InboxOutlined from "@mui/icons-material/InboxOutlined";
import { Button, Link, Stack, Typography } from "@mui/material";
import type { ReactNode } from "react";
import { Link as RouterLink } from "react-router";
import type { components } from "../../api/schema";
import { EmptyState } from "../../components/EmptyState";
import { GroupedList } from "../../components/GroupedList";
import { OfferPiece } from "../../components/OfferPiece";
import { offerSourceKind } from "../../components/offerSource";
import { DiscardingOffer } from "./DiscardingOffer";
import { groupByDay } from "./dayGroups";
import { discardReasonText } from "./discardReasons";
import type { SearchProfile } from "./filterRules";
import { OfferStrip } from "./OfferStrip";
import { SuggestedDiscard } from "./SuggestedDiscard";
import type { Offer, OfferView } from "./types";

export type JobBoard = Pick<components["schemas"]["JobBoardRead"], "id" | "import_method">;

/** What the pieces of the inbox need besides the offer: where offers come from and the profiles. */
export type OfferContext = { jobBoards: JobBoard[]; profiles: SearchProfile[]; now?: Date };

export type OfferActions = {
  onDiscard: (offer: Offer) => void;
  onPromote: (offer: Offer) => void;
  onRestore: (offer: Offer) => void;
};

type Props = OfferContext &
  OfferActions & {
    view: OfferView;
    offers: Offer[];
    /** One titled group of all the offers, instead of a group per day. */
    single?: { title: string; count: number };
    /** The offer open to discard, if any. */
    discardingId?: string | null;
    onCancelDiscard?: () => void;
    onDiscarded?: (offer: Offer) => void;
  };

const EMPTY: Record<OfferView, { icon: SvgIconComponent; text: string }> = {
  pending: { icon: InboxOutlined, text: "Import a job board or add an offer to fill the inbox." },
  filtered: {
    icon: FilterAltOutlined,
    text: "Imported offers that fit none of your search profiles are kept here.",
  },
  discarded: {
    icon: DeleteOutlineOutlined,
    text: "Discarded offers are kept here so you can restore them.",
  },
  promoted: { icon: ArrowUpwardOutlined, text: "Promoted offers become applications." },
};

/** One offer of the inbox as a piece, with its strip and the actions given. */
export function InboxOffer({
  offer,
  jobBoards,
  profiles,
  now = new Date(),
  actions,
  onDiscarded,
}: OfferContext & {
  offer: Offer;
  actions: ReactNode;
  /** Given, a pending offer with a suggested discard can be discarded as suggested. */
  onDiscarded?: (offer: Offer) => void;
}) {
  const sourceKind = offerSourceKind(offer, jobBoards);
  const isSuggested = offer.status === "pending" && offer.suggested_discard && onDiscarded;
  return (
    <OfferPiece
      offer={offer}
      sourceKind={sourceKind}
      now={now}
      actions={actions}
      strip={<OfferStrip offer={offer} sourceKind={sourceKind} profiles={profiles} />}
      footer={
        (offer.status === "discarded" && (
          <Typography variant="body2" color="text.secondary">
            Reason: {discardReasonText(offer)}
          </Typography>
        )) ||
        (isSuggested && <SuggestedDiscard offer={offer} onDiscarded={onDiscarded} />)
      }
    />
  );
}

// The offers of a view as pieces, grouped by the day they were added or in a single group.
export function OfferList({
  view,
  offers,
  jobBoards,
  profiles,
  now = new Date(),
  single,
  discardingId,
  onCancelDiscard = () => {},
  onDiscarded = () => {},
  ...actions
}: Props) {
  if (offers.length === 0) {
    const empty = EMPTY[view];
    return <EmptyState icon={empty.icon} title="No offers" text={empty.text} />;
  }
  const piece = (offer: Offer) =>
    offer.id === discardingId ? (
      <DiscardingOffer
        key={offer.id}
        offer={offer}
        jobBoards={jobBoards}
        profiles={profiles}
        now={now}
        onCancel={onCancelDiscard}
        onDiscarded={onDiscarded}
      />
    ) : (
      <InboxOffer
        key={offer.id}
        offer={offer}
        jobBoards={jobBoards}
        profiles={profiles}
        now={now}
        actions={<Actions offer={offer} {...actions} />}
        onDiscarded={onDiscarded}
      />
    );
  if (single) {
    return (
      <GroupedList title={single.title} count={single.count}>
        {offers.map(piece)}
      </GroupedList>
    );
  }
  return (
    <Stack spacing={4}>
      {groupByDay(offers, now).map((group) => (
        <GroupedList key={group.title} title={group.title} count={group.offers.length}>
          {group.offers.map(piece)}
        </GroupedList>
      ))}
    </Stack>
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
