import { Alert, Box, Button, Typography } from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import type { components } from "../../api/schema";

type Suggestion = components["schemas"]["CriteriaSuggestionRead"];
type Choice = "dismiss" | "exclude";

const offers = (count: number) => (count === 1 ? "1 offer" : `${count} offers`);

/** Why a word is suggested and what excluding it would do (specs/ui/metrics.feature). */
export function suggestionReason(suggestion: Suggestion): string {
  const { preview } = suggestion;
  const promoted =
    preview.promoted_filtered === 0
      ? "loses none you promoted"
      : `would have filtered ${preview.promoted_filtered} you promoted`;
  return `In ${suggestion.offer_ids.length} of the ${suggestion.discarded}. Takes ${offers(preview.leaving_pending)} out of Pending, ${promoted}.`;
}

// Counted from your decisions (specs/inbox/criteria_suggestions.feature); none is applied
// until "Exclude it", which is a logged criteria change.
export function SuggestedExclusions() {
  const queryClient = useQueryClient();
  const suggestions = useQuery({
    queryKey: ["criteria-suggestions"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/criteria-suggestions", {
        params: { query: { limit: 100 } },
      });
      if (error) throw error;
      return data.items;
    },
  });
  // The API's problem: its title says why the choice was rejected.
  const choose = useMutation<void, { title: string }, { suggestion: Suggestion; choice: Choice }>({
    mutationFn: async ({ suggestion, choice }) => {
      const { search_profile_id, word, excluded_keywords } = suggestion;
      const { error } =
        choice === "dismiss"
          ? await api.POST("/api/v1/criteria-suggestions/dismissals", {
              body: { search_profile_id, word },
            })
          : await api.POST("/api/v1/criteria-changes", {
              body: { search_profile_id, excluded_keywords },
            });
      if (error) throw error;
    },
    onSuccess: async () => {
      for (const key of ["criteria-suggestions", "criteria-changes", "offers", "search-profiles"]) {
        await queryClient.invalidateQueries({ queryKey: [key] });
      }
    },
  });

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
            <Typography variant="subtitle2">
              Suggested: exclude “{suggestion.word}” from {suggestion.search_profile_name}
            </Typography>
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
