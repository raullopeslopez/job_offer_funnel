import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Link,
  Stack,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";
import type { components } from "../../api/schema";
import type { Profile } from "./ProfilesGrid";

type JobBoardSearches = components["schemas"]["JobBoardSearchesRead"];

type Props = { profile: Profile | null; onClose: () => void };

/** The searches of a profile, one section per job board. */
export function SearchesDialog({ profile, onClose }: Props) {
  const searches = useQuery({
    queryKey: ["searches", profile?.id],
    enabled: profile !== null,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/search-profiles/{profile_id}/searches", {
        params: { path: { profile_id: profile?.id ?? "" } },
      });
      if (error) throw error;
      return data;
    },
  });

  return (
    <Dialog open={profile !== null} onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle>Searches for “{profile?.name}”</DialogTitle>
      <DialogContent>
        {searches.isPending && <CircularProgress />}
        {searches.error && <Alert severity="error">Could not load the searches</Alert>}
        {searches.data && (
          <Stack spacing={3}>
            {searches.data.work_modes.length > 0 && (
              <Typography color="text.secondary">
                Filter by work mode: {searches.data.work_modes.join(", ")}
              </Typography>
            )}
            {searches.data.job_boards.length === 0 ? (
              <Typography>No searches: there are no job boards yet.</Typography>
            ) : (
              searches.data.job_boards.map((board) => (
                <BoardSearches key={board.job_board_id} board={board} />
              ))
            )}
          </Stack>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}

function BoardSearches({ board }: { board: JobBoardSearches }) {
  const headingId = `board-${board.job_board_id}`;
  return (
    <Box component="section" aria-labelledby={headingId}>
      <Typography variant="h6" component="h3" id={headingId}>
        {board.job_board_name}
      </Typography>
      <Stack component="ul" spacing={1} sx={{ pl: 2, my: 1 }}>
        {board.searches.map((search) => (
          <li key={search.url}>
            <Link href={search.url} target="_blank" rel="noopener noreferrer">
              {search.query}
            </Link>
          </li>
        ))}
      </Stack>
    </Box>
  );
}
