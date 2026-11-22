import { Button } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";
import { Count, GroupedList } from "../../components/GroupedList";
import { offerSourceKind } from "../../components/offerSource";
import { KeyHint } from "./KeyHint";
import type { OfferContext, RowSelection } from "./OfferList";
import { OfferRow } from "./OfferRow";
import type { Offer } from "./types";

const SHOWN = 3;

/** The near misses, the most recent first. */
export function nearMissesQuery(limit: number) {
  return {
    queryKey: ["offers", "near-misses", limit],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/offers", {
        params: {
          query: {
            status: "pending",
            filtered: true,
            near_miss: true,
            limit,
          },
        },
      });
      if (error) throw error;
      return data;
    },
  };
}

export type NearMissActions = {
  onPromote: (offer: Offer) => void;
  onRightlyFiltered: (offer: Offer) => void;
};

/** What can be done with a near miss: promote it anyway, or leave it rightly filtered. */
export function NearMissButtons({
  offer,
  onPromote,
  onRightlyFiltered,
}: NearMissActions & { offer: Offer }) {
  return (
    <>
      <Button variant="outlined" aria-keyshortcuts="P" onClick={() => onPromote(offer)}>
        Promote anyway
        <KeyHint>P</KeyHint>
      </Button>
      <Button onClick={() => onRightlyFiltered(offer)}>Rightly filtered</Button>
    </>
  );
}

type Props = OfferContext & RowSelection;

// The last group of the pending view: the three most recent near misses, as rows that open in
// the reading pane.
export function MaybeGroup({ selectedId, onSelect, jobBoards, profiles, now }: Props) {
  const nearMisses = useQuery(nearMissesQuery(SHOWN));
  const page = nearMisses.data;
  if (!page || page.total === 0) return null;
  return (
    <GroupedList
      title="Maybe"
      count={page.total}
      heading={
        <>
          Maybe · <Count value={page.items.length} /> of <Count value={page.total} /> near misses
        </>
      }
      note="Filtered by a single rule. Promoting one tells the app the rule was too strict."
    >
      {page.items.map((offer) => (
        <OfferRow
          key={offer.id}
          offer={offer}
          sourceKind={offerSourceKind(offer, jobBoards)}
          profiles={profiles}
          selected={offer.id === selectedId}
          onSelect={onSelect}
          now={now}
        />
      ))}
    </GroupedList>
  );
}
