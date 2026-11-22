import { Alert, Box, Button, Stack, Typography } from "@mui/material";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../api/client";
import { whereText } from "../../components/OfferPiece";
import {
  CHOSEN_REASONS,
  DISCARD_REASON_LABELS,
  type DiscardReason,
  titleWords,
} from "./discardReasons";
import { ExclusionProposal, excludingWord } from "./ExclusionProposal";
import type { OfferContext } from "./OfferList";
import type { Offer } from "./types";

type Props = Pick<OfferContext, "profiles"> & {
  offer: Offer;
  onCancel: () => void;
  onDiscarded: (offer: Offer) => void;
};

// The reasons besides a word of the title, which has its own row of words.
const OTHER_REASONS = CHOSEN_REASONS.filter((reason) => reason !== "title_word");

// The reasons to discard an offer, in the action bar of the reading pane
// (specs/ui/inbox.feature): its title words are buttons under "A word in the title", and
// choosing a word or one of the other reasons discards. With a reference profile, a word first
// proposes excluding it from the profile.
export function DiscardChoices({ offer, profiles, onCancel, onDiscarded }: Props) {
  const [word, setWord] = useState<string | null>(null);
  const [isProposing, setIsProposing] = useState(false);
  const queryClient = useQueryClient();
  const profile = profiles.find((p) => p.id === offer.filter_reason?.search_profile_id);

  // The API's problem: its title says why the discard (or the exclusion) was rejected.
  const discard = useMutation<
    void,
    { title: string },
    { reason: DiscardReason; word?: string; exclude?: boolean }
  >({
    mutationFn: async ({ reason, word, exclude = false }) => {
      // The change first, so its log counts this offer among those leaving Pending
      // (specs/inbox/criteria_changes.feature).
      if (exclude && profile && word) {
        const { error } = await api.POST("/api/v1/criteria-changes", {
          body: {
            search_profile_id: profile.id,
            excluded_keywords: excludingWord(profile, word),
            offer_id: offer.id,
          },
        });
        if (error) throw error;
        void queryClient.invalidateQueries({ queryKey: ["search-profiles"] });
        void queryClient.invalidateQueries({ queryKey: ["criteria-changes"] });
      }
      const { error } = await api.POST("/api/v1/offers/{offer_id}/discard", {
        params: { path: { offer_id: offer.id } },
        body: reason === "title_word" ? { reason, word: word ?? null } : { reason },
      });
      if (error) throw error;
    },
    // Not returned: the discard is done once its request is, whatever the inbox does next.
    onSuccess: () => {
      onDiscarded(offer);
    },
  });

  // A word of the title is the reason "A word in the title": with a reference profile it
  // first proposes excluding the word from it.
  const chooseWord = (chosen: string) => {
    setWord(chosen);
    if (profile) setIsProposing(true);
    else discard.mutate({ reason: "title_word", word: chosen });
  };

  // What a reason refers to in this offer, when the piece knows it.
  const refersTo: Partial<Record<DiscardReason, string>> = {
    location: whereText(offer),
    company: offer.company,
  };

  return (
    <Box role="group" aria-label="Discard because" sx={{ width: 1 }}>
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
          onOnlyDiscard={() => discard.mutate({ reason: "title_word", word })}
          onDiscardAndExclude={() => discard.mutate({ reason: "title_word", word, exclude: true })}
        />
      ) : (
        <Stack spacing={2}>
          <Typography variant="subtitle2" component="p">
            Discard because
          </Typography>
          <Box role="group" aria-labelledby={`title-words-${offer.id}`}>
            <Typography
              id={`title-words-${offer.id}`}
              variant="caption"
              component="p"
              color="text.secondary"
              sx={{ mb: 1 }}
            >
              {DISCARD_REASON_LABELS.title_word}
            </Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75 }}>
              {titleWords(offer.title).map((candidate) => (
                <Button
                  key={candidate}
                  size="small"
                  variant="outlined"
                  disabled={discard.isPending}
                  onClick={() => chooseWord(candidate)}
                >
                  {candidate}
                </Button>
              ))}
            </Box>
          </Box>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "minmax(0, 1fr)", sm: "none" },
              gridAutoFlow: { xs: "row", sm: "column" },
              justifyContent: { sm: "start" },
              gap: 1,
            }}
          >
            {OTHER_REASONS.map((reason) => (
              <Button
                key={reason}
                aria-label={DISCARD_REASON_LABELS[reason]}
                variant="outlined"
                disabled={discard.isPending}
                onClick={() => discard.mutate({ reason })}
                sx={{ minHeight: 44, justifyContent: { xs: "space-between", sm: "center" } }}
              >
                {DISCARD_REASON_LABELS[reason]}
                {refersTo[reason] && (
                  <Box
                    component="span"
                    sx={{
                      display: { xs: "inline", sm: "none" },
                      ml: 2,
                      color: "text.secondary",
                      fontWeight: 400,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {refersTo[reason]}
                  </Box>
                )}
              </Button>
            ))}
          </Box>
          <Button
            disabled={discard.isPending}
            onClick={onCancel}
            sx={{ alignSelf: { xs: "stretch", sm: "flex-end" } }}
          >
            Cancel
          </Button>
        </Stack>
      )}
    </Box>
  );
}
