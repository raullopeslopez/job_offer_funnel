import { Alert, Box, Button, Typography } from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import type { components } from "../../api/schema";

type Change = components["schemas"]["CriteriaChangeRead"];
type Value = Change["before"];

const quote = (words: string[]) => words.map((word) => `“${word}”`).join(", ");
const asList = (value: Value) => (Array.isArray(value) ? value : []);

const LIST_WORDING = {
  excluded_keywords: { added: "Excluded", removed: "Stopped excluding" },
  titles: { added: "Added the title", removed: "Removed the title" },
  keywords: { added: "Added the keyword", removed: "Removed the keyword" },
} as const;

/** What a change did to its rule, in the words of specs/ui/metrics.feature. */
export function describeChange({ rule, before, after }: Change): string {
  if (rule === "location") return after ? `Location: ${after}` : "No location";
  if (rule === "work_modes") {
    const modes = asList(after);
    return modes.length > 0 ? `Work modes: ${modes.join(", ")}` : "Any work mode";
  }
  const wording = LIST_WORDING[rule];
  const added = asList(after).filter((word) => !asList(before).includes(word));
  const removed = asList(before).filter((word) => !asList(after).includes(word));
  return [
    added.length > 0 ? `${wording.added} ${quote(added)}` : null,
    removed.length > 0 ? `${wording.removed} ${quote(removed)}` : null,
  ]
    .filter(Boolean)
    .join(" · ");
}

const DAY_MS = 86_400_000;

function dayOf(createdAt: string, now: Date): string {
  const day = new Date(createdAt);
  const days = Math.round(
    (new Date(now.toDateString()).getTime() - new Date(day.toDateString()).getTime()) / DAY_MS,
  );
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  return day.toLocaleDateString("en", { month: "short", day: "numeric" });
}

/** The effect line of a change: when, and what it did to Pending and to the promoted. */
export function effectOf(change: Change, now = new Date()): string {
  return `${dayOf(change.created_at, now)} · took ${change.leaving_pending} out of Pending · lost ${change.promoted_filtered} promoted`;
}

export function CriteriaChanges() {
  const queryClient = useQueryClient();
  const changes = useQuery({
    queryKey: ["criteria-changes"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/criteria-changes", {
        params: { query: { limit: 100 } },
      });
      if (error) throw error;
      return data.items;
    },
  });
  // The API's problem: its title says why the undo was rejected.
  const undo = useMutation<void, { title: string }, string>({
    mutationFn: async (changeId) => {
      const { error } = await api.DELETE("/api/v1/criteria-changes/{change_id}", {
        params: { path: { change_id: changeId } },
      });
      if (error) throw error;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["criteria-changes"] });
      await queryClient.invalidateQueries({ queryKey: ["offers"] });
      await queryClient.invalidateQueries({ queryKey: ["search-profiles"] });
    },
  });

  return (
    <Box component="section" aria-labelledby="criteria-changes" sx={{ mb: 4 }}>
      <Typography id="criteria-changes" variant="h6" component="h3">
        Changes to your criteria
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
        Each change with what it did, so you can tell if it helped.
      </Typography>
      {undo.isError && (
        <Alert severity="error" sx={{ mb: 1.5 }}>
          {undo.error.title}
        </Alert>
      )}
      {changes.data?.length === 0 && (
        <Typography color="text.secondary">No changes yet.</Typography>
      )}
      <Box
        component="ul"
        aria-label="Changes to your criteria"
        sx={{ listStyle: "none", p: 0, m: 0 }}
      >
        {changes.data?.map((change) => (
          <Box
            component="li"
            key={change.id}
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 2,
              py: 1,
              borderTop: 1,
              borderColor: "divider",
            }}
          >
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography variant="body2">{describeChange(change)}</Typography>
              <Typography variant="caption" color="text.secondary">
                {effectOf(change)}
              </Typography>
            </Box>
            <Button size="small" disabled={undo.isPending} onClick={() => undo.mutate(change.id)}>
              Undo
            </Button>
          </Box>
        ))}
      </Box>
    </Box>
  );
}
