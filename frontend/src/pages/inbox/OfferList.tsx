import type { SvgIconComponent } from "@mui/icons-material";
import ArrowUpwardOutlined from "@mui/icons-material/ArrowUpwardOutlined";
import DeleteOutlineOutlined from "@mui/icons-material/DeleteOutlineOutlined";
import FilterAltOutlined from "@mui/icons-material/FilterAltOutlined";
import InboxOutlined from "@mui/icons-material/InboxOutlined";
import type { components } from "../../api/schema";
import { EmptyState } from "../../components/EmptyState";
import { GroupedList } from "../../components/GroupedList";
import { offerSourceKind } from "../../components/offerSource";
import { groupByDay, groupByVerdict } from "./dayGroups";
import type { SearchProfile } from "./filterRules";
import { OfferRow } from "./OfferRow";
import type { Offer, OfferView } from "./types";
import { groupVariants, variantKey } from "./variants";

export type JobBoard = Pick<components["schemas"]["JobBoardRead"], "id" | "import_method">;

/** What the offers of the inbox need besides the offer: where offers come from and the profiles. */
export type OfferContext = {
  jobBoards: JobBoard[];
  profiles: SearchProfile[];
  now?: Date;
  triageRunning?: boolean;
};

export type OfferActions = {
  onDiscard: (offer: Offer) => void;
  onPromote: (offer: Offer) => void;
  onRestore: (offer: Offer) => void;
};

/** Which row is selected, and what choosing a row does. */
export type RowSelection = {
  selectedId: string | null;
  onSelect: (offer: Offer) => void;
};

type Props = OfferContext &
  RowSelection & {
    view: OfferView;
    offers: Offer[];
    /** One titled group of all the offers, instead of a group per day. */
    single?: { title: string; count: number };
    /** Listed by verdict: once one has a verdict, grouped by verdict instead of by day. */
    byVerdict?: boolean;
    /** Listed with their variants together: those next to each other show as one row. */
    variants?: boolean;
    /** The roles whose variants are open, by `variantKey`. */
    openVariants?: string[];
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

// The offers of a view as rows, grouped by the day they were added, by verdict or in a single
// group. The offer of the selected row shows in the reading pane.
export function OfferList({
  view,
  offers,
  jobBoards,
  profiles,
  now = new Date(),
  single,
  byVerdict = false,
  variants = false,
  openVariants = [],
  selectedId,
  onSelect,
}: Props) {
  if (offers.length === 0) {
    const empty = EMPTY[view];
    return <EmptyState icon={empty.icon} title="No offers" text={empty.text} />;
  }
  const row = (offer: Offer, more = 0, indented = false) => (
    <OfferRow
      key={offer.id}
      offer={offer}
      sourceKind={offerSourceKind(offer, jobBoards)}
      profiles={profiles}
      selected={offer.id === selectedId}
      onSelect={onSelect}
      variants={more}
      indented={indented}
      now={now}
    />
  );
  // A run of variants is the row of the first of them; open, the rows of the others follow.
  const rows = (listed: Offer[]) =>
    !variants
      ? listed.map((offer) => row(offer))
      : groupVariants(listed).flatMap(({ first, offers: run }) => [
          row(first, run.length - 1),
          ...(openVariants.includes(variantKey(first))
            ? run.slice(1).map((offer) => row(offer, 0, true))
            : []),
        ]);
  if (single) {
    return (
      <GroupedList title={single.title} count={single.count}>
        {rows(offers)}
      </GroupedList>
    );
  }
  const groups =
    byVerdict && offers.some((offer) => offer.triage)
      ? groupByVerdict(offers)
      : groupByDay(offers, now);
  return (
    <>
      {groups.map((group) => (
        <GroupedList key={group.title} title={group.title} count={group.offers.length}>
          {rows(group.offers)}
        </GroupedList>
      ))}
    </>
  );
}
