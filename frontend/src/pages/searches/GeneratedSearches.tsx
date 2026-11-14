import OpenInNewOutlined from "@mui/icons-material/OpenInNewOutlined";
import { Alert, Box, Button, CircularProgress, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useId } from "react";
import { api } from "../../api/client";
import type { components } from "../../api/schema";
import { mono } from "../../theme";

type JobBoardSearches = components["schemas"]["JobBoardSearchesRead"];

// The searches of a profile for the job boards checked by hand, one block per job board.
export function GeneratedSearches({ profileId }: { profileId: string }) {
  const titleId = useId();
  const searches = useQuery({
    queryKey: ["searches", profileId],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/search-profiles/{profile_id}/searches", {
        params: { path: { profile_id: profileId } },
      });
      if (error) throw error;
      return data;
    },
  });

  return (
    <Box component="section" aria-labelledby={titleId}>
      <Typography id={titleId} variant="subtitle1" component="h3" sx={{ fontWeight: 600, mb: 1 }}>
        Generated searches
      </Typography>
      {searches.isPending && <CircularProgress size={24} />}
      {searches.error && <Alert severity="error">Could not load the searches</Alert>}
      {searches.data &&
        (searches.data.job_boards.length === 0 ? (
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            No searches: there are no job boards yet.
          </Typography>
        ) : (
          <Stack spacing={1.5}>
            {searches.data.job_boards.map((board) => (
              <BoardSearches key={board.job_board_id} board={board} />
            ))}
          </Stack>
        ))}
    </Box>
  );
}

function BoardSearches({ board }: { board: JobBoardSearches }) {
  const headingId = useId();
  return (
    <Box component="section" aria-labelledby={headingId}>
      <Box sx={{ display: "flex", alignItems: "baseline", gap: 1 }}>
        <Typography id={headingId} component="h4" sx={{ fontWeight: 600 }}>
          {board.job_board_name}
        </Typography>
        <Typography variant="body2" sx={{ fontFamily: mono, color: "text.secondary" }}>
          {board.syntax}
        </Typography>
      </Box>
      <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>
        {board.searches.map((search) => (
          <Box
            component="li"
            key={search.url}
            sx={{ display: "flex", alignItems: "center", gap: 2, py: 0.5 }}
          >
            <Typography
              variant="body2"
              sx={{ fontFamily: mono, flex: 1, minWidth: 0, overflowWrap: "anywhere" }}
            >
              {search.query}
            </Typography>
            <Button
              size="small"
              variant="outlined"
              href={search.url}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`Open search “${search.query}”`}
              endIcon={<OpenInNewOutlined aria-hidden />}
              sx={{ flexShrink: 0 }}
            >
              Open search
            </Button>
          </Box>
        ))}
      </Box>
    </Box>
  );
}
