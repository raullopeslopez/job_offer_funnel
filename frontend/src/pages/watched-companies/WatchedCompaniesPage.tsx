import HubOutlined from "@mui/icons-material/HubOutlined";
import VisibilityOffOutlined from "@mui/icons-material/VisibilityOffOutlined";
import VisibilityOutlined from "@mui/icons-material/VisibilityOutlined";
import { Button, Stack, Typography } from "@mui/material";
import { DataGrid, type GridColDef } from "@mui/x-data-grid";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../api/client";
import type { components } from "../../api/schema";
import { CompanyAvatar } from "../../components/CompanyAvatar";
import { EmptyState } from "../../components/EmptyState";
import { RowAction, RowActions, rowActionsSx } from "../../components/RowActions";
import { Meta, Sep, TwoLineCell } from "../../components/TwoLineCell";
import { ImportWatchedCompanyDialog } from "./ImportWatchedCompanyDialog";
import { StopWatchingDialog } from "./StopWatchingDialog";
import { WatchCompanyDialog } from "./WatchCompanyDialog";

export type WatchedCompany = components["schemas"]["WatchedCompanyRead"];

function NoWatchedCompanies() {
  return (
    <EmptyState
      icon={VisibilityOutlined}
      title="No watched companies"
      text="Watch a company to import offers straight from its careers page."
    />
  );
}

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
    {
      field: "name",
      headerName: "Company",
      flex: 2,
      sortable: false,
      renderCell: ({ row }) => (
        <TwoLineCell
          lead={<CompanyAvatar name={row.name} />}
          primary={row.name}
          secondary={
            <>
              <Meta icon={HubOutlined}>{row.ats}</Meta>
              <Sep />
              <Meta mono>{row.board || "—"}</Meta>
            </>
          }
        />
      ),
    },
    {
      field: "actions",
      headerName: "",
      width: 150,
      sortable: false,
      renderCell: ({ row }) => (
        <Stack direction="row" spacing={0.5} sx={{ height: "100%", alignItems: "center" }}>
          <Button size="small" onClick={() => setImporting(row)}>
            Import
          </Button>
          <RowActions>
            <RowAction
              icon={VisibilityOffOutlined}
              label={`Stop watching “${row.name}”`}
              onClick={() => setStopping(row)}
            />
          </RowActions>
        </Stack>
      ),
    },
  ];

  return (
    <>
      <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography variant="h5" component="h2">
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
        rowHeight={64}
        sx={rowActionsSx}
        slots={{ noRowsOverlay: NoWatchedCompanies }}
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
