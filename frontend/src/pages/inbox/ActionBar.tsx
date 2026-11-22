import { Alert, Box, Button, Link, Typography } from "@mui/material";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Link as RouterLink } from "react-router";
import { api } from "../../api/client";
import { mono } from "../../theme";
import { DiscardChoices } from "./DiscardChoices";
import { DISCARD_REASON_LABELS } from "./discardReasons";
import { type NearMissActions, NearMissButtons } from "./MaybeGroup";
import type { OfferActions, OfferContext } from "./OfferList";
import type { Offer } from "./types";

type Props = Omit<OfferActions, "onDiscard"> &
  NearMissActions &
  Pick<OfferContext, "profiles"> & {
    offer: Offer;
    /** Which offer of the view it is: "3 of 7". */
    position?: { index: number; total: number };
    nearMiss: boolean;
    onDiscarded: (offer: Offer) => void;
  };

// The actions of the offer open in the reading pane (specs/ui/inbox.feature): a bar fixed at the
// foot of the pane, with a line above and no box. "Discard" opens its reasons in the bar itself.
// With a suggested discard, "Discard: {reason}" is the main action, always by my click.
export function ActionBar({
  offer,
  position,
  nearMiss,
  profiles,
  onDiscarded,
  onPromote,
  onRestore,
  onRightlyFiltered,
}: Props) {
  const [isDiscarding, setIsDiscarding] = useState(false);
  const suggestion = offer.status === "pending" && !nearMiss ? offer.suggested_discard : null;
  const discardAsSuggested = useMutation<void, { title: string }>({
    mutationFn: async () => {
      if (!suggestion) return;
      const { reason, evidence } = suggestion;
      const { error } = await api.POST("/api/v1/offers/{offer_id}/discard", {
        params: { path: { offer_id: offer.id } },
        body: reason === "title_word" ? { reason, word: evidence } : { reason },
      });
      if (error) throw error;
    },
    // Not returned: the discard is done once its request is, whatever the inbox does next.
    onSuccess: () => {
      onDiscarded(offer);
    },
  });

  return (
    <Box
      role="group"
      aria-label="Offer actions"
      sx={{
        position: "sticky",
        bottom: 0,
        mt: "auto",
        py: 1.5,
        borderTop: 1,
        borderColor: "divider",
        bgcolor: "background.default",
      }}
    >
      {discardAsSuggested.isError && (
        <Alert severity="error" sx={{ mb: 1.5 }}>
          {discardAsSuggested.error.title}
        </Alert>
      )}
      {isDiscarding ? (
        <DiscardChoices
          offer={offer}
          profiles={profiles}
          onCancel={() => setIsDiscarding(false)}
          onDiscarded={(discarded) => {
            setIsDiscarding(false);
            onDiscarded(discarded);
          }}
        />
      ) : (
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 1,
            "& .MuiButton-root": { minHeight: { xs: 44, sm: "auto" } },
          }}
        >
          {position && (
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ fontFamily: mono, mr: "auto", pr: 1 }}
            >
              {position.index + 1} of {position.total}
            </Typography>
          )}
          {nearMiss ? (
            <NearMissButtons
              offer={offer}
              onPromote={onPromote}
              onRightlyFiltered={onRightlyFiltered}
            />
          ) : offer.status === "pending" ? (
            <>
              {suggestion ? (
                <>
                  <Button
                    variant="contained"
                    loading={discardAsSuggested.isPending}
                    onClick={() => discardAsSuggested.mutate()}
                  >
                    Discard: {DISCARD_REASON_LABELS[suggestion.reason]}
                  </Button>
                  <Button variant="outlined" onClick={() => onPromote(offer)}>
                    Promote
                  </Button>
                  <Button onClick={() => setIsDiscarding(true)}>Other reason</Button>
                </>
              ) : (
                <>
                  <Button variant="contained" onClick={() => onPromote(offer)}>
                    Promote
                  </Button>
                  <Button variant="outlined" onClick={() => setIsDiscarding(true)}>
                    Discard
                  </Button>
                </>
              )}
            </>
          ) : offer.status === "discarded" ? (
            <Button variant="outlined" onClick={() => onRestore(offer)}>
              Restore
            </Button>
          ) : (
            offer.application_id && (
              <Link component={RouterLink} to={`/applications/${offer.application_id}`}>
                Open application
              </Link>
            )
          )}
        </Box>
      )}
    </Box>
  );
}
