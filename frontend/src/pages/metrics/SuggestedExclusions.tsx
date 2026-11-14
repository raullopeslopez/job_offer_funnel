import { Alert, Box, Button, Typography } from "@mui/material";
import {
  type CriteriaSuggestion,
  suggestionEffect,
  useCriteriaSuggestions,
  useSuggestionChoice,
} from "../../components/criteriaSuggestions";

/** Why a word is suggested and what excluding it would do (specs/ui/metrics.feature): the
 * counted ones say in how many discarded offers it is, the triager's say its why. */
export function suggestionReason(suggestion: CriteriaSuggestion): string {
  const why =
    suggestion.source === "triager"
      ? suggestion.why
      : `In ${suggestion.offer_ids.length} of the ${suggestion.discarded}.`;
  return `${why} ${suggestionEffect(suggestion)}`;
}

/** "Suggested" when counted, "AI suggests" when the offer triager suggests it. */
export function suggestionTitle({ source, word, search_profile_name }: CriteriaSuggestion): string {
  const who = source === "triager" ? "AI suggests" : "Suggested";
  return `${who}: exclude “${word}” from ${search_profile_name}`;
}

// Counted from your decisions or suggested by the offer triager
// (specs/inbox/criteria_suggestions.feature); none is applied until "Exclude it", which is a
// logged criteria change.
export function SuggestedExclusions() {
  const suggestions = useCriteriaSuggestions();
  const choose = useSuggestionChoice();

  if (!suggestions.data?.length) return null;
  return (
    <>
      {choose.isError && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {choose.error.title}
        </Alert>
      )}
      <Box component="ul" aria-label="Suggestions" sx={{ listStyle: "none", p: 0, mt: 2, mb: 0 }}>
        {suggestions.data.map((suggestion) => (
          <Box
            component="li"
            key={`${suggestion.search_profile_id}-${suggestion.word}`}
            sx={{ py: 1.5, borderTop: 1, borderColor: "divider" }}
          >
            <Typography variant="subtitle2">{suggestionTitle(suggestion)}</Typography>
            <Typography variant="body2" color="text.secondary">
              {suggestionReason(suggestion)}
            </Typography>
            <Box sx={{ display: "flex", gap: 1, mt: 1 }}>
              <Button
                size="small"
                disabled={choose.isPending}
                onClick={() => choose.mutate({ suggestion, choice: "dismiss" })}
              >
                Not now
              </Button>
              <Button
                size="small"
                variant="contained"
                disabled={choose.isPending}
                onClick={() => choose.mutate({ suggestion, choice: "exclude" })}
              >
                Exclude it
              </Button>
            </Box>
          </Box>
        ))}
      </Box>
    </>
  );
}
