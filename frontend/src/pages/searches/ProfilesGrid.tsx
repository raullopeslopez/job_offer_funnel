import { Button, Stack } from "@mui/material";
import { DataGrid, type GridColDef, type GridPaginationModel } from "@mui/x-data-grid";
import type { components } from "../../api/schema";

export type Profile = components["schemas"]["SearchProfileRead"];

type Props = {
  profiles: Profile[];
  total: number;
  loading: boolean;
  pagination: GridPaginationModel;
  onPaginationChange: (model: GridPaginationModel) => void;
  onSearches: (profile: Profile) => void;
  onEdit: (profile: Profile) => void;
  onDelete: (profile: Profile) => void;
};

const joined = (values: string[]) => values.join(", ");

export function ProfilesGrid({ profiles, total, loading, pagination, ...props }: Props) {
  const columns: GridColDef<Profile>[] = [
    { field: "name", headerName: "Name", flex: 1, sortable: false },
    { field: "titles", headerName: "Titles", flex: 2, sortable: false, valueFormatter: joined },
    { field: "keywords", headerName: "Keywords", flex: 1, sortable: false, valueFormatter: joined },
    {
      field: "excluded_keywords",
      headerName: "Excluded",
      flex: 1,
      sortable: false,
      valueFormatter: joined,
    },
    { field: "location", headerName: "Location", flex: 1, sortable: false },
    {
      field: "work_modes",
      headerName: "Work modes",
      flex: 1,
      sortable: false,
      valueFormatter: joined,
    },
    {
      field: "actions",
      headerName: "",
      width: 260,
      sortable: false,
      renderCell: ({ row }) => (
        <Stack direction="row" spacing={1} sx={{ height: "100%", alignItems: "center" }}>
          <Button size="small" onClick={() => props.onSearches(row)}>
            Searches
          </Button>
          <Button size="small" color="inherit" onClick={() => props.onEdit(row)}>
            Edit
          </Button>
          <Button size="small" color="inherit" onClick={() => props.onDelete(row)}>
            Delete
          </Button>
        </Stack>
      ),
    },
  ];

  return (
    <DataGrid
      rows={profiles}
      columns={columns}
      rowCount={total}
      loading={loading}
      paginationMode="server"
      paginationModel={pagination}
      onPaginationModelChange={props.onPaginationChange}
      pageSizeOptions={[pagination.pageSize]}
      disableColumnMenu
      disableRowSelectionOnClick
      autoHeight
      localeText={{ noRowsLabel: "No profiles" }}
    />
  );
}
