import { Button, Stack, Typography } from "@mui/material";
import type { GridPaginationModel } from "@mui/x-data-grid";
import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../api/client";
import { DeleteProfileDialog } from "./DeleteProfileDialog";
import { ProfileDialog } from "./ProfileDialog";
import { type Profile, ProfilesGrid } from "./ProfilesGrid";
import { SearchesDialog } from "./SearchesDialog";

const PAGE_SIZE = 20;

export function SearchesPage() {
  const queryClient = useQueryClient();
  const [pagination, setPagination] = useState<GridPaginationModel>({
    page: 0,
    pageSize: PAGE_SIZE,
  });
  // "new" opens the form empty; a profile opens it to edit that profile.
  const [editing, setEditing] = useState<Profile | "new" | null>(null);
  const [deleting, setDeleting] = useState<Profile | null>(null);
  const [showingSearches, setShowingSearches] = useState<Profile | null>(null);

  const profiles = useQuery({
    queryKey: ["search-profiles", pagination.page, pagination.pageSize],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/search-profiles", {
        params: {
          query: { limit: pagination.pageSize, offset: pagination.page * pagination.pageSize },
        },
      });
      if (error) throw error;
      return data;
    },
    placeholderData: keepPreviousData,
  });

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ["search-profiles"] });
    await queryClient.invalidateQueries({ queryKey: ["searches"] });
  };

  return (
    <>
      <Stack direction="row" sx={{ alignItems: "center", mb: 2 }}>
        <Typography variant="h4" component="h1" sx={{ flexGrow: 1 }}>
          Profiles
        </Typography>
        <Button variant="contained" onClick={() => setEditing("new")}>
          New profile
        </Button>
      </Stack>
      <Typography color="text.secondary" sx={{ mb: 2 }}>
        Each search profile builds the search for every job board.
      </Typography>

      <ProfilesGrid
        profiles={profiles.data?.items ?? []}
        total={profiles.data?.total ?? 0}
        loading={profiles.isFetching}
        pagination={pagination}
        onPaginationChange={setPagination}
        onSearches={setShowingSearches}
        onEdit={setEditing}
        onDelete={setDeleting}
      />

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
      <SearchesDialog profile={showingSearches} onClose={() => setShowingSearches(null)} />
    </>
  );
}
