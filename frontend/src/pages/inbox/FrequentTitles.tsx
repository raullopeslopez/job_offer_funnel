import { Alert, Box, Button, Typography } from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import type { components } from "../../api/schema";
import { mono } from "../../theme";

type SearchProfile = components["schemas"]["SearchProfileRead"];
type FrequentTitle = components["schemas"]["FrequentTitleRead"];

const offers = (count: number) => (count === 1 ? "1 offer" : `${count} offers`);

/** "{k} mention python · {j} remote and open to Spain", from what the profile asks. */
export function titleLine(title: FrequentTitle, profile: SearchProfile): string {
  const parts: string[] = [];
  if (profile.keywords.length > 0) {
    parts.push(`${title.with_keywords} mention ${profile.keywords.join(" and ").toLowerCase()}`);
  }
  const asks = [
    profile.work_modes.length > 0 ? profile.work_modes.join(" or ") : null,
    profile.location ? `open to ${profile.location}` : null,
  ].filter(Boolean);
  parts.push(
    `${title.reading_passes} ${asks.length > 0 ? asks.join(" and ") : "pass the reading"}`,
  );
  return parts.join(" · ");
}

// specs/ui/inbox.feature: in Filtered, the titles that keep coming without a title of the
// profile (specs/inbox/frequent_titles.feature); adding one is a criteria change.
function ProfileTitles({ profile, named }: { profile: SearchProfile; named: boolean }) {
  const queryClient = useQueryClient();
  const found = useQuery({
    queryKey: ["offers", "frequent-titles", profile.id],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/offers/frequent-titles", {
        params: { query: { search_profile_id: profile.id } },
      });
      if (error) throw error;
      return data;
    },
  });
  // The API's problem: its title says why the change was rejected.
  const add = useMutation<void, { title: string }, FrequentTitle>({
    mutationFn: async (title) => {
      const { error } = await api.POST("/api/v1/criteria-changes", {
        body: { search_profile_id: profile.id, titles: title.titles },
      });
      if (error) throw error;
    },
    onSuccess: async () => {
      for (const key of ["offers", "search-profiles", "criteria-changes"]) {
        await queryClient.invalidateQueries({ queryKey: [key] });
      }
    },
  });

  if (!found.data || found.data.titles.length === 0) return null;
  const heading = `No title of yours${named ? ` in ${profile.name}` : ""} · ${offers(found.data.offers)}`;
  return (
    <Box component="section" aria-label={heading} sx={{ mb: 3 }}>
      <Typography variant="h6" component="h2">
        {heading}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        Most frequent titles
      </Typography>
      {add.isError && (
        <Alert severity="error" sx={{ mb: 1 }}>
          {add.error.title}
        </Alert>
      )}
      <Box component="ul" aria-label="Most frequent titles" sx={{ listStyle: "none", p: 0, m: 0 }}>
        {found.data.titles.map((title) => (
          <Box
            component="li"
            key={title.title}
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 2,
              py: 1,
              borderTop: 1,
              borderColor: "divider",
            }}
          >
            <Typography sx={{ fontFamily: mono, minWidth: "2rem" }}>{title.offers}</Typography>
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography variant="body2">{title.title}</Typography>
              <Typography variant="caption" color="text.secondary">
                {titleLine(title, profile)}
              </Typography>
            </Box>
            <Button
              size="small"
              variant="outlined"
              disabled={add.isPending}
              onClick={() => add.mutate(title)}
            >
              Add title · brings {title.preview.entering_pending} to Pending
            </Button>
          </Box>
        ))}
      </Box>
    </Box>
  );
}

export function FrequentTitles({ profiles }: { profiles: SearchProfile[] }) {
  return (
    <>
      {profiles.map((profile) => (
        <ProfileTitles key={profile.id} profile={profile} named={profiles.length > 1} />
      ))}
    </>
  );
}
