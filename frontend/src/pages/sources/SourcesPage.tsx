import { Box, Typography } from "@mui/material";
import { JobBoardsSection } from "../settings/JobBoardsSection";
import { WatchedCompaniesPage } from "../watched-companies/WatchedCompaniesPage";

// The job boards and the watched companies, one below the other (specs/ui/sources.feature).
export function SourcesPage() {
  return (
    <>
      <Typography variant="h4" component="h1" sx={{ mb: 2 }}>
        Sources
      </Typography>
      <Typography variant="h5" component="h2" sx={{ mb: 2 }}>
        Job boards
      </Typography>
      <JobBoardsSection />
      <Box sx={{ mt: 6 }}>
        <WatchedCompaniesPage />
      </Box>
    </>
  );
}
