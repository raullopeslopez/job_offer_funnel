import { Tab, Tabs, Typography } from "@mui/material";
import { useState } from "react";
import { CompaniesSection } from "./CompaniesSection";
import { JobBoardsSection } from "./JobBoardsSection";

type Section = "companies" | "job-boards";

export function SettingsPage() {
  const [section, setSection] = useState<Section>("companies");

  return (
    <>
      <Typography variant="h4" component="h1" sx={{ mb: 2 }}>
        Settings
      </Typography>
      <Tabs value={section} onChange={(_, value: Section) => setSection(value)} sx={{ mb: 2 }}>
        <Tab value="companies" label="Companies" />
        <Tab value="job-boards" label="Job boards" />
      </Tabs>
      {section === "companies" ? <CompaniesSection /> : <JobBoardsSection />}
    </>
  );
}
