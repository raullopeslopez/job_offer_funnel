import { Button, Stack, Typography } from "@mui/material";
import { DataGrid, type GridColDef } from "@mui/x-data-grid";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../api/client";
import type { components } from "../../api/schema";
import { ImportWatchedCompanyDialog } from "./ImportWatchedCompanyDialog";
import { StopWatchingDialog } from "./StopWatchingDialog";
import { WatchCompanyDialog } from "./WatchCompanyDialog";

export type WatchedCompany = components["schemas"]["WatchedCompanyRead"];

export function WatchedCompaniesPage() {
  const queryClient = useQueryClient();
  const [watching, setWatching] = useState(false);
  const [importing, setImporting] = useState<WatchedCompany | null>(null);
  const [stopping, setStopping] = useState<WatchedCompany | null>(null);

  // The API lists them by name, all at once.
  const companies = useQuery({
    queryKey: ["watched-companies"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/watched-companies");
      if (error) throw error;
      return data;
    },
  });

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["watched-companies"] });

  const columns: GridColDef<WatchedCompany>[] = [
    { field: "name", headerName: "Name", flex: 1, sortable: false },
    { field: "ats", headerName: "ATS", flex: 1, sortable: false },
    { field: "board", headerName: "Board", flex: 1, sortable: false },
    {
      field: "actions",
      headerName: "",
      width: 220,
      sortable: false,
      renderCell: ({ row }) => (
        <Stack direction="row" spacing={1} sx={{ height: "100%", alignItems: "center" }}>
          <Button size="small" color="inherit" onClick={() => setImporting(row)}>
            Import
          </Button>
          <Button size="small" color="inherit" onClick={() => setStopping(row)}>
            Stop watching
          </Button>
        </Stack>
      ),
    },
  ];

  return (
    <>
      <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography variant="h4" component="h1">
          Watched companies
        </Typography>
        <Button variant="contained" onClick={() => setWatching(true)}>
          Watch a company
        </Button>
      </Stack>

      <DataGrid
        rows={companies.data ?? []}
        columns={columns}
        loading={companies.isFetching}
        disableColumnMenu
        disableRowSelectionOnClick
        hideFooter
        autoHeight
        localeText={{ noRowsLabel: "No watched companies" }}
      />

      {watching && (
        <WatchCompanyDialog
          onClose={() => setWatching(false)}
          onWatched={async () => {
            setWatching(false);
            await refresh();
          }}
        />
      )}
      {importing && (
        <ImportWatchedCompanyDialog company={importing} onClose={() => setImporting(null)} />
      )}
      <StopWatchingDialog
        company={stopping}
        onClose={() => setStopping(null)}
        onStopped={async () => {
          setStopping(null);
          await refresh();
        }}
      />
    </>
  );
}
