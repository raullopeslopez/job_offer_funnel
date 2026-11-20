import { Alert, Box, Button, Stack, Typography } from "@mui/material";
import { useMutation } from "@tanstack/react-query";
import { api } from "../../api/client";
import type { components } from "../../api/schema";
import {
  acceptLabel,
  suggestionChange,
  suggestionEffect,
  useCriteriaSuggestions,
  useSuggestionChoice,
} from "../../components/criteriaSuggestions";
import { offerShape, offerType } from "../../theme";
import { DISCARD_REASON_LABELS } from "./discardReasons";
import type { Offer } from "./types";

type Props = { offer: Offer; onDiscarded?: (offer: Offer) => void };
type Why = components["schemas"]["WhyRead"];
type Confidence = components["schemas"]["Confidence"];

const CONFIDENCE: Record<Confidence, { label: string; bars: number }> = {
  low: { label: "Low", bars: 1 },
  medium: { label: "Medium", bars: 2 },
  high: { label: "High", bars: 3 },
};

/** How sure the triager is: three bars, as many filled as its level, and the level. */
function ConfidenceMeter({ confidence }: { confidence: Confidence }) {
  const { label, bars } = CONFIDENCE[confidence];
  return (
    <Box
      role="img"
      aria-label={`${label} confidence`}
      sx={{ display: "inline-flex", alignItems: "center", gap: 1 }}
    >
      <Box aria-hidden sx={{ display: "inline-flex", gap: "3px" }}>
        {[1, 2, 3].map((bar) => (
          <Box
            key={bar}
            sx={{
              width: 14,
              height: 5,
              borderRadius: 3,
              bgcolor: bar <= bars ? "text.primary" : "divider",
            }}
          />
        ))}
      </Box>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
    </Box>
  );
}

/** One side of the triage: "Why yes: {why}" or "Why not: {why}", and its quote. */
function WhyLine({ side, why }: { side: "yes" | "no"; why: Why }) {
  return (
    <Typography variant="body2">
      <Box
        component="span"
        sx={{ fontWeight: 500, color: side === "yes" ? "tone.green.fg" : "tone.red.fg" }}
      >
        {side === "yes" ? "Why yes:" : "Why not:"}
      </Box>{" "}
      {why.why}
      {why.quote && (
        <Box component="span" sx={{ color: "text.secondary" }}>
          {" "}
          “{why.quote}”
        </Box>
      )}
    </Typography>
  );
}

// The AI section of a pending offer or a near miss (specs/ui/inbox.feature): its verdict and
// confidence, why yes and why not with their quotes, and "Discard: {reason}" with a suggested
// discard (with title_word the word goes with it); and, for an offer a criteria suggestion
// comes from (a KO offer, or an OK near miss), "Improve the filter", a criteria change made
// from this offer.
export function TriageVerdict({ offer, onDiscarded }: Props) {
  const triage = offer.triage;
  const suggestion = offer.suggested_discard;
  const canImprove = triage?.verdict === (offer.filtered ? "ok" : "ko");
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

  if (!triage) return null;
  const isOk = triage.verdict === "ok";
  const error = discard.error ?? choose.error;
  return (
    <Stack spacing={1.5}>
      {error && <Alert severity="error">{error.title}</Alert>}
      <Box
        component="section"
        aria-label="AI verdict"
        sx={{
          borderTop: 1,
          borderColor: "divider",
          pt: 1.75,
          display: "grid",
          gridTemplateColumns: { xs: "1fr", sm: "132px minmax(0, 1fr) auto" },
          gap: { xs: 1.5, sm: 2.5 },
          alignItems: "start",
        }}
      >
        <Stack
          direction={{ xs: "row", sm: "column" }}
          spacing={{ xs: 1.5, sm: 1 }}
          sx={{ alignItems: { xs: "center", sm: "flex-start" } }}
        >
          <Box
            component="span"
            sx={{
              display: "inline-flex",
              alignItems: "center",
              height: offerShape.tagHeight,
              px: 1.25,
              borderRadius: offerShape.tagRadius,
              bgcolor: isOk ? "tone.green.bg" : "tone.red.bg",
              color: isOk ? "tone.green.fg" : "tone.red.fg",
              ...offerType.tag,
              fontWeight: 600,
            }}
          >
            AI: {triage.verdict.toUpperCase()}
          </Box>
          {triage.confidence && <ConfidenceMeter confidence={triage.confidence} />}
        </Stack>
        <Stack spacing={0.75} sx={{ minWidth: 0 }}>
          {triage.why_yes && <WhyLine side="yes" why={triage.why_yes} />}
          {triage.why_not && <WhyLine side="no" why={triage.why_not} />}
        </Stack>
        {suggestion && (
          <Button
            size="small"
            variant="outlined"
            loading={discard.isPending}
            onClick={() => discard.mutate()}
            sx={{ alignSelf: "center", justifySelf: { xs: "start", sm: "end" } }}
          >
            Discard: {DISCARD_REASON_LABELS[suggestion.reason]}
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
