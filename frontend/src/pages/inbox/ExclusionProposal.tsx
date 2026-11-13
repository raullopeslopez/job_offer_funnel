import { Alert, Box, Button, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";
import type { components } from "../../api/schema";

type SearchProfile = components["schemas"]["SearchProfileRead"];
type Preview = components["schemas"]["CriteriaPreviewRead"];

type Props = {
  word: string;
  profile: SearchProfile;
  isBusy: boolean;
  onOnlyDiscard: () => void;
  onDiscardAndExclude: () => void;
};

const offers = (count: number) => (count === 1 ? "1 offer" : `${count} offers`);

/** What excluding the word would do, in the words of specs/ui/inbox.feature. */
export function previewEffect(preview: Preview): string {
  const promoted =
    preview.promoted_filtered === 0
      ? "Loses none you promoted."
      : `Would have filtered ${preview.promoted_filtered} you promoted.`;
  const discarded =
    preview.discarded_filtered === 0
      ? "None you discarded had it."
      : `${preview.discarded_filtered} you discarded had it.`;
  return `Takes ${offers(preview.leaving_pending)} out of Pending. ${promoted} ${discarded}`;
}

export const excludingWord = (profile: SearchProfile, word: string) => [
  ...profile.excluded_keywords,
  word,
];

// The proposal of "A word in the title" (specs/ui/inbox.feature): excluding the word from
// the offer's reference profile, with the effect of the change before confirming it.
export function ExclusionProposal({
  word,
  profile,
  isBusy,
  onOnlyDiscard,
  onDiscardAndExclude,
}: Props) {
  const preview = useQuery({
    queryKey: ["criteria-preview", profile.id, word],
    queryFn: async () => {
      const { data, error } = await api.POST("/api/v1/offers/criteria-previews", {
        body: { search_profile_id: profile.id, excluded_keywords: excludingWord(profile, word) },
      });
      if (error) throw error;
      return data;
    },
  });

  return (
    <Box role="group" aria-label="Exclude from the profile">
      <Typography variant="subtitle2">
        Exclude “{word}” from the profile {profile.name}?
      </Typography>
      {preview.data && (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          {previewEffect(preview.data)}
        </Typography>
      )}
      {preview.isError && (
        <Alert severity="error" sx={{ mt: 1 }}>
          The effect of the change could not be worked out.
        </Alert>
      )}
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mt: 1.5 }}>
        <Button size="small" variant="outlined" disabled={isBusy} onClick={onOnlyDiscard}>
          Only discard this one
        </Button>
        <Button size="small" variant="contained" disabled={isBusy} onClick={onDiscardAndExclude}>
          Discard and exclude “{word}”
        </Button>
      </Box>
    </Box>
  );
}
