import { Alert, Box, Button, Paper, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";
import {
  suggestionEffect,
  useCriteriaSuggestions,
  useSuggestionChoice,
} from "../../components/criteriaSuggestions";

// The criteria suggestions of the offer triager, above the offers, one at a time
// (specs/ui/inbox.feature): "Not now", or "Exclude it", a logged criteria change. Without an
// offer triager there are none.
export function TriagerSuggestion() {
  const triager = useQuery({
    queryKey: ["offers", "triager"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/offers/triager");
      if (error) throw error;
      return data;
    },
  });
  const suggestions = useCriteriaSuggestions(triager.data?.is_available === true);
  const choose = useSuggestionChoice();
  const suggestion = suggestions.data?.find((s) => s.source === "triager");

  if (!suggestion) return null;
  return (
    <Paper component="section" variant="outlined" sx={{ p: 2, mb: 3 }} aria-label="AI suggestion">
      {choose.isError && (
        <Alert severity="error" sx={{ mb: 1.5 }}>
          {choose.error.title}
        </Alert>
      )}
      <Typography variant="subtitle2">
        AI suggests: exclude “{suggestion.word}” from {suggestion.search_profile_name}
      </Typography>
      <Typography variant="body2">{suggestion.why}</Typography>
      <Typography variant="body2" color="text.secondary">
        {suggestionEffect(suggestion)}
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
    </Paper>
  );
}
