import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { components } from "../api/schema";

export type CriteriaSuggestion = components["schemas"]["CriteriaSuggestionRead"];
type Choice = "dismiss" | "exclude";

const offers = (count: number) => (count === 1 ? "1 offer" : `${count} offers`);

/** Whether it lets more offers in: all but excluding a word the profile does not exclude. */
export function isRelaxing({ rule, word, after }: CriteriaSuggestion): boolean {
  return rule !== "excluded_keywords" || !(Array.isArray(after) && after.includes(word));
}

/** The change, as "Improve the filter" or "AI suggests" says it (specs/ui/inbox.feature). */
export function suggestionChange(suggestion: CriteriaSuggestion): string {
  const { rule, word, search_profile_name: profile } = suggestion;
  if (rule === "keywords") return `stop asking for the keyword “${word}” in ${profile}`;
  if (rule === "work_modes") return `accept the work mode “${word}” in ${profile}`;
  return isRelaxing(suggestion)
    ? `stop excluding “${word}” in ${profile}`
    : `exclude “${word}” from ${profile}`;
}

/** "Exclude it" to tighten the filter, "Relax it" to let more offers in. */
export function acceptLabel(suggestion: CriteriaSuggestion): string {
  return isRelaxing(suggestion) ? "Relax it" : "Exclude it";
}

/** What the change would do (specs/ui/metrics.feature, specs/ui/inbox.feature). */
export function suggestionEffect(suggestion: CriteriaSuggestion): string {
  const { preview } = suggestion;
  if (isRelaxing(suggestion)) {
    const discarded =
      preview.discarded_fitting === 0
        ? "none you discarded"
        : `${preview.discarded_fitting} you discarded`;
    return `Brings ${preview.entering_pending} into Pending, ${discarded}.`;
  }
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
      const { search_profile_id, rule, word, after } = suggestion;
      const { error } =
        choice === "dismiss"
          ? await api.POST("/api/v1/criteria-suggestions/dismissals", {
              body: { search_profile_id, rule, word },
            })
          : await api.POST("/api/v1/criteria-changes", {
              body: {
                search_profile_id,
                [rule]: after,
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
