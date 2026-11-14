import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { components } from "../api/schema";

export type CriteriaSuggestion = components["schemas"]["CriteriaSuggestionRead"];
type Choice = "dismiss" | "exclude";

const offers = (count: number) => (count === 1 ? "1 offer" : `${count} offers`);

/** What excluding the word would do (specs/ui/metrics.feature, specs/ui/inbox.feature). */
export function suggestionEffect({ preview }: CriteriaSuggestion): string {
  const promoted =
    preview.promoted_filtered === 0
      ? "loses none you promoted"
      : `would have filtered ${preview.promoted_filtered} you promoted`;
  return `Takes ${offers(preview.leaving_pending)} out of Pending, ${promoted}.`;
}

/** The criteria suggestions (specs/inbox/criteria_suggestions.feature), counted or from the
 * offer triager; none is applied until it is accepted. */
export function useCriteriaSuggestions(enabled = true) {
  return useQuery({
    queryKey: ["criteria-suggestions"],
    enabled,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/criteria-suggestions", {
        params: { query: { limit: 100 } },
      });
      if (error) throw error;
      return data.items;
    },
  });
}

/** "Not now", or accepting a suggestion: a logged criteria change, made from the offer given. */
export function useSuggestionChoice() {
  const queryClient = useQueryClient();
  // The API's problem: its title says why the choice was rejected.
  return useMutation<
    void,
    { title: string },
    { suggestion: CriteriaSuggestion; choice: Choice; offerId?: string }
  >({
    mutationFn: async ({ suggestion, choice, offerId }) => {
      const { search_profile_id, word, excluded_keywords } = suggestion;
      const { error } =
        choice === "dismiss"
          ? await api.POST("/api/v1/criteria-suggestions/dismissals", {
              body: { search_profile_id, word },
            })
          : await api.POST("/api/v1/criteria-changes", {
              body: {
                search_profile_id,
                excluded_keywords,
                ...(offerId ? { offer_id: offerId } : {}),
              },
            });
      if (error) throw error;
    },
    onSuccess: async () => {
      for (const key of ["criteria-suggestions", "criteria-changes", "offers", "search-profiles"]) {
        await queryClient.invalidateQueries({ queryKey: [key] });
      }
    },
  });
}
