import ManageSearchOutlined from "@mui/icons-material/ManageSearchOutlined";
import { Alert, Box, Button, CircularProgress, Stack, Typography } from "@mui/material";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../api/client";
import { EmptyState } from "../../components/EmptyState";
import { groupedPiecesSx } from "../../components/GroupedList";
import { DeleteProfileDialog } from "./DeleteProfileDialog";
import { ProfileDialog } from "./ProfileDialog";
import { ProfilePiece } from "./ProfilePiece";
import type { Profile } from "./types";

// The most the API returns in one page: one user has far fewer profiles.
const LIMIT = 100;

export function SearchesPage() {
  const queryClient = useQueryClient();
  // "new" opens the form empty; a profile opens it to edit that profile.
  const [editing, setEditing] = useState<Profile | "new" | null>(null);
  const [deleting, setDeleting] = useState<Profile | null>(null);

  const profiles = useQuery({
    queryKey: ["search-profiles"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/search-profiles", {
        params: { query: { limit: LIMIT } },
      });
      if (error) throw error;
      return data;
    },
  });

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ["search-profiles"] });
    await queryClient.invalidateQueries({ queryKey: ["searches"] });
  };

  const items = profiles.data?.items ?? [];

  return (
    <>
      <Stack
        direction={{ xs: "column", md: "row" }}
        spacing={2}
        sx={{ justifyContent: "space-between", alignItems: { md: "flex-end" }, mb: 5 }}
      >
        <Box>
          <Typography variant="h4" component="h1" sx={{ mb: 1 }}>
            Profiles
          </Typography>
          <Typography sx={{ color: "text.secondary" }}>
            What you are looking for. A profile decides which imported offers fit, and writes the
            search for every job board you check by hand.
          </Typography>
        </Box>
        <Button variant="contained" onClick={() => setEditing("new")} sx={{ flexShrink: 0 }}>
          New profile
        </Button>
      </Stack>

      {profiles.isPending && <CircularProgress />}
      {profiles.error && <Alert severity="error">Could not load the profiles</Alert>}
      {profiles.data &&
        (items.length === 0 ? (
          <EmptyState
            icon={ManageSearchOutlined}
            title="No profiles"
            text="A profile turns titles and keywords into a search for every job board."
          />
        ) : (
          <Box sx={groupedPiecesSx}>
            {items.map((profile, index) => (
              <ProfilePiece
                key={profile.id}
                profile={profile}
                open={index === 0}
                onEdit={() => setEditing(profile)}
                onDelete={() => setDeleting(profile)}
              />
            ))}
          </Box>
        ))}

      {editing && (
        <ProfileDialog
          profile={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={async () => {
            setEditing(null);
            await refresh();
          }}
        />
      )}
      <DeleteProfileDialog
        profile={deleting}
        onClose={() => setDeleting(null)}
        onDeleted={async () => {
          setDeleting(null);
          await refresh();
        }}
      />
    </>
  );
}
