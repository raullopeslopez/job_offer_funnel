import { Typography } from "@mui/material";
import { CompaniesSection } from "../settings/CompaniesSection";

export function CompaniesPage() {
  return (
    <>
      <Typography variant="h4" component="h1" sx={{ mb: 2 }}>
        Companies
      </Typography>
      <CompaniesSection />
    </>
  );
}
