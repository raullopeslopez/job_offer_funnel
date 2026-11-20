import { Box, Button, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";
import { groupedPiecesSx } from "../../components/GroupedList";
import { mono } from "../../theme";
import { InboxOffer, type OfferContext } from "./OfferList";
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
      <Button variant="outlined" onClick={() => onPromote(offer)}>
        Promote anyway
      </Button>
      <Button onClick={() => onRightlyFiltered(offer)}>Rightly filtered</Button>
    </>
  );
}

type Props = OfferContext & NearMissActions;

// The last group of the pending view: the three most recent near misses.
export function MaybeGroup({ onPromote, onRightlyFiltered, ...context }: Props) {
  const nearMisses = useQuery(nearMissesQuery(SHOWN));
  const page = nearMisses.data;
  if (!page || page.total === 0) return null;
  return (
    <Box component="section" aria-label="Maybe" sx={{ mt: 4 }}>
      <Typography variant="h6" component="h2">
        Maybe ·{" "}
        <Box component="span" sx={{ fontFamily: mono, fontWeight: 500 }}>
          {page.items.length}
        </Box>{" "}
        of{" "}
        <Box component="span" sx={{ fontFamily: mono, fontWeight: 500 }}>
          {page.total}
        </Box>{" "}
        near misses
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 1.5 }}>
        Filtered by a single rule. Promoting one tells the app the rule was too strict.
      </Typography>
      <Box sx={groupedPiecesSx}>
        {page.items.map((offer) => (
          <InboxOffer
            key={offer.id}
            offer={offer}
            {...context}
            actions={
              <NearMissButtons
                offer={offer}
                onPromote={onPromote}
                onRightlyFiltered={onRightlyFiltered}
              />
            }
          />
        ))}
      </Box>
    </Box>
  );
}
