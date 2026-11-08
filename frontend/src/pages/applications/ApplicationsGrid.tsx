import { Link } from "@mui/material";
import { DataGrid, type GridColDef, type GridPaginationModel } from "@mui/x-data-grid";
import { Link as RouterLink } from "react-router";
import { type Application, formatDate } from "./options";

type Props = {
  applications: Application[];
  total: number;
  loading: boolean;
  pagination: GridPaginationModel;
  onPaginationChange: (model: GridPaginationModel) => void;
};

const columns: GridColDef<Application>[] = [
  {
    field: "role",
    headerName: "Role",
    flex: 2,
    sortable: false,
    renderCell: ({ row }) => (
      <Link component={RouterLink} to={`/applications/${row.id}`}>
        {row.role}
      </Link>
    ),
  },
  { field: "company_name", headerName: "Company", flex: 1, sortable: false },
  { field: "stage", headerName: "Stage", flex: 1, sortable: false },
  { field: "outcome", headerName: "Outcome", flex: 1, sortable: false },
  { field: "channel", headerName: "Channel", flex: 1, sortable: false },
  { field: "priority", headerName: "Priority", width: 110, sortable: false },
  {
    field: "created_at",
    headerName: "Added",
    width: 130,
    sortable: false,
    valueFormatter: (value: string) => formatDate(value),
  },
];

export function ApplicationsGrid({ applications, total, loading, pagination, ...props }: Props) {
  return (
    <DataGrid
      rows={applications}
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
      localeText={{ noRowsLabel: "No applications" }}
    />
  );
}
