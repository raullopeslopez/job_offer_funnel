import { Alert, Box, Button, Typography } from "@mui/material";
import { useMutation } from "@tanstack/react-query";
import { api } from "../../api/client";
import { DISCARD_REASON_LABELS } from "./discardReasons";
import type { Offer } from "./types";

type Props = { offer: Offer; onDiscarded: (offer: Offer) => void };

// What the offer triager suggests for a pending offer (specs/ui/inbox.feature), and its
// discard in one click: with title_word the evidence is the word.
export function SuggestedDiscard({ offer, onDiscarded }: Props) {
  const suggestion = offer.suggested_discard;
  const discard = useMutation<void, { title: string }>({
    mutationFn: async () => {
      if (!suggestion) return;
      const { reason, evidence } = suggestion;
      const { error } = await api.POST("/api/v1/offers/{offer_id}/discard", {
        params: { path: { offer_id: offer.id } },
        body: reason === "title_word" ? { reason, word: evidence } : { reason },
      });
      if (error) throw error;
    },
    onSuccess: () => onDiscarded(offer),
  });

  if (!suggestion) return null;
  return (
    <Box>
      {discard.isError && (
        <Alert severity="error" sx={{ mb: 1.5 }}>
          {discard.error.title}
        </Alert>
      )}
      <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 1 }}>
        <Typography variant="body2" color="text.secondary">
          Suggested discard: {DISCARD_REASON_LABELS[suggestion.reason]} — “{suggestion.evidence}”
        </Typography>
        <Button
          size="small"
          variant="outlined"
          loading={discard.isPending}
          onClick={() => discard.mutate()}
          sx={{ ml: "auto" }}
        >
          Discard as suggested
        </Button>
      </Box>
    </Box>
  );
}
