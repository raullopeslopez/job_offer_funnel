import { Button, Stack } from "@mui/material";
import { DataGrid, type GridColDef, type GridPaginationModel } from "@mui/x-data-grid";
import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../api/client";
import type { components } from "../../api/schema";
import { CompanyDialog } from "./CompanyDialog";
import { DeleteCompanyDialog } from "./DeleteCompanyDialog";

export type Company = components["schemas"]["CompanyRead"];

const PAGE_SIZE = 20;

export function CompaniesSection() {
  const queryClient = useQueryClient();
  const [pagination, setPagination] = useState<GridPaginationModel>({
    page: 0,
    pageSize: PAGE_SIZE,
  });
  // "new" opens the form empty; a company opens it to edit that company.
  const [editing, setEditing] = useState<Company | "new" | null>(null);
  const [deleting, setDeleting] = useState<Company | null>(null);

  const companies = useQuery({
    queryKey: ["companies", pagination.page, pagination.pageSize],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/companies", {
        params: {
          query: { limit: pagination.pageSize, offset: pagination.page * pagination.pageSize },
        },
      });
      if (error) throw error;
      return data;
    },
    placeholderData: keepPreviousData,
  });

  // Also refreshes the company options of the application form.
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["companies"] });

  const columns: GridColDef<Company>[] = [
    { field: "name", headerName: "Name", flex: 1, sortable: false },
    { field: "website", headerName: "Website", flex: 2, sortable: false },
    {
      field: "actions",
      headerName: "",
      width: 180,
      sortable: false,
      renderCell: ({ row }) => (
        <Stack direction="row" spacing={1} sx={{ height: "100%", alignItems: "center" }}>
          <Button size="small" color="inherit" onClick={() => setEditing(row)}>
            Edit
          </Button>
          <Button size="small" color="inherit" onClick={() => setDeleting(row)}>
            Delete
          </Button>
        </Stack>
      ),
    },
  ];

  return (
    <>
      <Stack direction="row" sx={{ justifyContent: "flex-end", mb: 2 }}>
        <Button variant="contained" onClick={() => setEditing("new")}>
          New company
        </Button>
      </Stack>

      <DataGrid
        rows={companies.data?.items ?? []}
        columns={columns}
        rowCount={companies.data?.total ?? 0}
        loading={companies.isFetching}
        paginationMode="server"
        paginationModel={pagination}
        onPaginationModelChange={setPagination}
        pageSizeOptions={[pagination.pageSize]}
        disableColumnMenu
        disableRowSelectionOnClick
        autoHeight
        localeText={{ noRowsLabel: "No companies" }}
      />

      {editing && (
        <CompanyDialog
          company={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={async () => {
            setEditing(null);
            await refresh();
          }}
        />
      )}
      <DeleteCompanyDialog
        company={deleting}
        onClose={() => setDeleting(null)}
        onDeleted={async () => {
          setDeleting(null);
          await refresh();
        }}
      />
    </>
  );
}
