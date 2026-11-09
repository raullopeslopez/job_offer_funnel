import { Tab, Tabs, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../api/client";
import { TabLabel } from "../../components/TabLabel";
import { CompaniesSection } from "./CompaniesSection";
import { JobBoardsSection } from "./JobBoardsSection";

type Section = "companies" | "job-boards";

// Totals for the tab counts. Their keys extend the ones the sections invalidate, so they refresh too.
function useCompaniesTotal() {
  return useQuery({
    queryKey: ["companies", "total"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/companies", {
        params: { query: { limit: 1 } },
      });
      if (error) throw error;
      return data.total;
    },
  });
}

function useJobBoardsTotal() {
  return useQuery({
    queryKey: ["job-boards", "total"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/job-boards", {
        params: { query: { limit: 1 } },
      });
      if (error) throw error;
      return data.total;
    },
  });
}

export function SettingsPage() {
  const [section, setSection] = useState<Section>("companies");
  const companiesTotal = useCompaniesTotal();
  const jobBoardsTotal = useJobBoardsTotal();

  return (
    <>
      <Typography variant="h4" component="h1" sx={{ mb: 2 }}>
        Settings
      </Typography>
      <Tabs value={section} onChange={(_, value: Section) => setSection(value)} sx={{ mb: 2 }}>
        <Tab
          value="companies"
          label={<TabLabel label="Companies" count={companiesTotal.data ?? 0} />}
        />
        <Tab
          value="job-boards"
          label={<TabLabel label="Job boards" count={jobBoardsTotal.data ?? 0} />}
        />
      </Tabs>
      {section === "companies" ? <CompaniesSection /> : <JobBoardsSection />}
    </>
  );
}
