import { Alert, Box, Button, Typography } from "@mui/material";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../api/client";
import { OfferPiece } from "../../components/OfferPiece";
import { offerSourceKind } from "../../components/offerSource";
import {
  CHOSEN_REASONS,
  DISCARD_REASON_LABELS,
  type DiscardReason,
  titleWords,
} from "./discardReasons";
import { ExclusionProposal, excludingWord } from "./ExclusionProposal";
import type { OfferContext } from "./OfferList";
import { OfferStrip } from "./OfferStrip";
import type { Offer } from "./types";

type Props = OfferContext & {
  offer: Offer;
  onCancel: () => void;
  onDiscarded: (offer: Offer) => void;
};

// The piece open to discard (specs/ui/inbox.feature): the words of the title are buttons,
// and choosing a reason discards; "A word in the title" needs a word marked first. With a
// reference profile, that reason first proposes excluding the word from it.
export function DiscardingOffer({ offer, jobBoards, profiles, now, onCancel, onDiscarded }: Props) {
  const [word, setWord] = useState<string | null>(null);
  const [isProposing, setIsProposing] = useState(false);
  const queryClient = useQueryClient();
  const sourceKind = offerSourceKind(offer, jobBoards);
  const profile = profiles.find((p) => p.id === offer.filter_reason?.search_profile_id);

  // The API's problem: its title says why the discard (or the exclusion) was rejected.
  const discard = useMutation<
    void,
    { title: string },
    { reason: DiscardReason; exclude?: boolean }
  >({
    mutationFn: async ({ reason, exclude = false }) => {
      const { error } = await api.POST("/api/v1/offers/{offer_id}/discard", {
        params: { path: { offer_id: offer.id } },
        body: reason === "title_word" ? { reason, word } : { reason },
      });
      if (error) throw error;
      if (!exclude || !profile || word === null) return;
      const { error: excludeError } = await api.PATCH("/api/v1/search-profiles/{profile_id}", {
        params: { path: { profile_id: profile.id } },
        body: { excluded_keywords: excludingWord(profile, word) },
      });
      if (excludeError) throw excludeError;
      await queryClient.invalidateQueries({ queryKey: ["search-profiles"] });
    },
    onSuccess: () => onDiscarded(offer),
  });

  const choose = (reason: DiscardReason) => {
    if (reason === "title_word" && profile) setIsProposing(true);
    else discard.mutate({ reason });
  };

  const words = (
    <Box component="span" sx={{ display: "inline-flex", flexWrap: "wrap", gap: 0.75 }}>
      {titleWords(offer.title).map((candidate) => {
        const pressed = candidate === word;
        return (
          <Button
            key={candidate}
            size="small"
            variant={pressed ? "contained" : "outlined"}
            aria-pressed={pressed}
            onClick={() => setWord(pressed ? null : candidate)}
          >
            {candidate}
          </Button>
        );
      })}
    </Box>
  );

  return (
    <OfferPiece
      offer={offer}
      sourceKind={sourceKind}
      now={now}
      heading={words}
      strip={<OfferStrip offer={offer} sourceKind={sourceKind} profiles={profiles} />}
      footer={
        <Box role="group" aria-label="Discard because">
          {discard.isError && (
            <Alert severity="error" sx={{ mb: 1.5 }}>
              {discard.error.title}
            </Alert>
          )}
          {isProposing && profile && word !== null ? (
            <ExclusionProposal
              word={word}
              profile={profile}
              isBusy={discard.isPending}
              onOnlyDiscard={() => discard.mutate({ reason: "title_word" })}
              onDiscardAndExclude={() => discard.mutate({ reason: "title_word", exclude: true })}
            />
          ) : (
            <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 1 }}>
              <Typography variant="body2" color="text.secondary">
                Discard because
              </Typography>
              {CHOSEN_REASONS.map((reason) => (
                <Button
                  key={reason}
                  size="small"
                  variant="outlined"
                  disabled={discard.isPending || (reason === "title_word" && word === null)}
                  onClick={() => choose(reason)}
                >
                  {DISCARD_REASON_LABELS[reason]}
                </Button>
              ))}
              <Button size="small" onClick={onCancel} sx={{ ml: "auto" }}>
                Cancel
              </Button>
            </Box>
          )}
        </Box>
      }
    />
  );
}
