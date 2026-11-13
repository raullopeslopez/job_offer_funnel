import type { SvgIconComponent } from "@mui/icons-material";
import ArrowUpwardOutlined from "@mui/icons-material/ArrowUpwardOutlined";
import DeleteOutlineOutlined from "@mui/icons-material/DeleteOutlineOutlined";
import FilterAltOutlined from "@mui/icons-material/FilterAltOutlined";
import InboxOutlined from "@mui/icons-material/InboxOutlined";
import { Button, Link, Stack, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router";
import type { components } from "../../api/schema";
import { EmptyState } from "../../components/EmptyState";
import { GroupedList } from "../../components/GroupedList";
import { OfferPiece } from "../../components/OfferPiece";
import { offerSourceKind } from "../../components/offerSource";
import { groupByDay } from "./dayGroups";
import { ReadingStrip } from "./ReadingStrip";
import type { Offer, OfferView } from "./types";

type JobBoard = Pick<components["schemas"]["JobBoardRead"], "id" | "import_method">;

type Props = {
  view: OfferView;
  offers: Offer[];
  jobBoards: JobBoard[];
  now?: Date;
  onDiscard: (offer: Offer) => void;
  onPromote: (offer: Offer) => void;
  onRestore: (offer: Offer) => void;
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

// The offers of a view as pieces, grouped by the day they were added.
export function OfferList({ view, offers, jobBoards, now = new Date(), ...actions }: Props) {
  if (offers.length === 0) {
    const empty = EMPTY[view];
    return <EmptyState icon={empty.icon} title="No offers" text={empty.text} />;
  }
  return (
    <Stack spacing={4}>
      {groupByDay(offers, now).map((group) => (
        <GroupedList key={group.title} title={group.title} count={group.offers.length}>
          {group.offers.map((offer) => (
            <OfferPiece
              key={offer.id}
              offer={offer}
              sourceKind={offerSourceKind(offer, jobBoards)}
              now={now}
              actions={<Actions offer={offer} {...actions} />}
              strip={<ReadingStrip readings={offer.readings} />}
              footer={
                offer.status === "discarded" && (
                  <Typography variant="body2" color="text.secondary">
                    Reason: {offer.discard_reason || "—"}
                  </Typography>
                )
              }
            />
          ))}
        </GroupedList>
      ))}
    </Stack>
  );
}

function Actions({
  offer,
  onDiscard,
  onPromote,
  onRestore,
}: { offer: Offer } & Pick<Props, "onDiscard" | "onPromote" | "onRestore">) {
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
