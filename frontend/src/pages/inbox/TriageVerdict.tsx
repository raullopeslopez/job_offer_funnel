import { Alert, Box, Button, Stack, Typography } from "@mui/material";
import type { components } from "../../api/schema";
import {
  acceptLabel,
  suggestionChange,
  suggestionEffect,
  useCriteriaSuggestions,
  useSuggestionChoice,
} from "../../components/criteriaSuggestions";
import { offerShape, offerType } from "../../theme";
import type { Offer } from "./types";

type Props = { offer: Offer };
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

export function TriagePending() {
  return (
    <Stack
      direction="row"
      spacing={1.5}
      sx={{ alignItems: "center", borderTop: 1, borderColor: "divider", pt: 1.75 }}
    >
      <Box
        aria-hidden="true"
        sx={{
          display: "flex",
          alignItems: "center",
          gap: "4px",
          height: offerShape.tagHeight,
          px: 1.25,
          bgcolor: "fill",
          borderRadius: offerShape.tagRadius,
          "& span": { width: 5, height: 5, bgcolor: "text.secondary", borderRadius: "50%" },
          "@media (prefers-reduced-motion: no-preference)": {
            "& span": { animation: "triagePulse 1.2s ease-in-out infinite" },
            "& span:nth-of-type(2)": { animationDelay: "150ms" },
            "& span:nth-of-type(3)": { animationDelay: "300ms" },
            "@keyframes triagePulse": { "50%": { transform: "translateY(-3px)", opacity: 0.45 } },
          },
        }}
      >
        <span />
        <span />
        <span />
      </Box>
      <Typography variant="body2" color="text.secondary">
        Triage in progress · Awaiting verdict
      </Typography>
    </Stack>
  );
}

/** One side of the triage: "Why yes: {why}" or "Why not: {why}", with its quote under it. */
function WhyLine({ side, why }: { side: "yes" | "no"; why: Why }) {
  return (
    <Box>
      <Typography variant="body1">
        <Box
          component="span"
          sx={{ fontWeight: 500, color: side === "yes" ? "tone.green.fg" : "tone.red.fg" }}
        >
          {side === "yes" ? "Why yes:" : "Why not:"}
        </Box>{" "}
        {why.why}
      </Typography>
      {why.quote && (
        <Typography
          component="blockquote"
          variant="body1"
          color="text.secondary"
          sx={{ mx: 0, mt: 0.75, mb: 0, pl: 1.75, borderLeft: 1, borderColor: "divider" }}
        >
          “{why.quote}”
        </Typography>
      )}
    </Box>
  );
}

// The AI section of a pending offer or a near miss (specs/ui/inbox.feature): its verdict and
// confidence, why yes and why not with their quotes; and, for an offer a criteria suggestion
// comes from (a KO offer, or an OK near miss), "Improve the filter", a criteria change made
// from this offer.
export function TriageVerdict({ offer }: Props) {
  const triage = offer.triage;
  const canImprove = triage?.verdict === (offer.filtered ? "ok" : "ko");
  const suggestions = useCriteriaSuggestions(canImprove);
  const improvement = suggestions.data?.find(
    (s) => s.source === "triager" && s.offer_ids.includes(offer.id),
  );
  const choose = useSuggestionChoice();
  if (!triage) return null;
  const isOk = triage.verdict === "ok";
  const error = choose.error;
  return (
    <Stack spacing={1.5}>
      {error && <Alert severity="error">{error.title}</Alert>}
      <Box
        component="section"
        aria-label="AI verdict"
        sx={{ borderTop: 1, borderColor: "text.primary", pt: 2.5, mt: 4 }}
      >
        <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 1.25 }}>
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
          {isOk && offer.filtered && (
            <Typography variant="caption" sx={{ color: "tone.green.fg" }}>
              · worth rescuing
            </Typography>
          )}
        </Box>
        <Stack spacing={2} sx={{ mt: 2, minWidth: 0 }}>
          {triage.why_yes && <WhyLine side="yes" why={triage.why_yes} />}
          {triage.why_not && <WhyLine side="no" why={triage.why_not} />}
        </Stack>
        {improvement && (
          <Box
            sx={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              gap: 1,
              mt: 2.5,
              pt: 2,
              borderTop: 1,
              borderColor: "divider",
            }}
          >
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
      </Box>
    </Stack>
  );
}
