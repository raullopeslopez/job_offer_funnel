import { Alert, Box, Button, Stack, Typography } from "@mui/material";
import { useMutation } from "@tanstack/react-query";
import { api } from "../../api/client";
import {
  acceptLabel,
  suggestionChange,
  suggestionEffect,
  useCriteriaSuggestions,
  useSuggestionChoice,
} from "../../components/criteriaSuggestions";
import { DISCARD_REASON_LABELS } from "./discardReasons";
import type { Offer } from "./types";

type Props = { offer: Offer; onDiscarded?: (offer: Offer) => void };

/** "AI: OK — why", or "AI: KO — why" with the suggested discard if its evidence holds. */
export function verdictText({ triage, suggested_discard }: Offer): string {
  if (!triage) return "";
  const said = `AI: ${triage.verdict.toUpperCase()} — ${triage.why}`;
  if (!suggested_discard) return said;
  const { reason, evidence } = suggested_discard;
  return `${said} ${DISCARD_REASON_LABELS[reason]} — “${evidence}”`;
}

// What the offer triager says of a pending offer or a near miss (specs/ui/inbox.feature):
// its verdict and why; "Discard as suggested" with a suggested discard (with title_word the
// evidence is the word); and, for an offer a criteria suggestion comes from (a KO offer, or
// an OK near miss), "Improve the filter", a criteria change made from this offer.
export function TriageVerdict({ offer, onDiscarded }: Props) {
  const suggestion = offer.suggested_discard;
  const canImprove = offer.triage?.verdict === (offer.filtered ? "ok" : "ko");
  const suggestions = useCriteriaSuggestions(canImprove);
  const improvement = suggestions.data?.find(
    (s) => s.source === "triager" && s.offer_ids.includes(offer.id),
  );
  const choose = useSuggestionChoice();
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
    onSuccess: () => onDiscarded?.(offer),
  });

  if (!offer.triage) return null;
  const error = discard.error ?? choose.error;
  return (
    <Stack spacing={1}>
      {error && <Alert severity="error">{error.title}</Alert>}
      <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 1 }}>
        <Typography variant="body2" color="text.secondary">
          {verdictText(offer)}
        </Typography>
        {suggestion && (
          <Button
            size="small"
            variant="outlined"
            loading={discard.isPending}
            onClick={() => discard.mutate()}
            sx={{ ml: "auto" }}
          >
            Discard as suggested
          </Button>
        )}
      </Box>
      {improvement && (
        <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 1 }}>
          <Box>
            <Typography variant="body2">
              Improve the filter: {suggestionChange(improvement)}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {suggestionEffect(improvement)}
            </Typography>
          </Box>
          <Button
            size="small"
            variant="contained"
            loading={choose.isPending}
            onClick={() =>
              choose.mutate({ suggestion: improvement, choice: "exclude", offerId: offer.id })
            }
            sx={{ ml: "auto" }}
          >
            {acceptLabel(improvement)}
          </Button>
        </Box>
      )}
    </Stack>
  );
}
