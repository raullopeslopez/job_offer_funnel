import WorkOutlined from "@mui/icons-material/WorkOutlined";
import { Box, Link } from "@mui/material";
import {
  DataGrid,
  type GridColDef,
  type GridColumnVisibilityModel,
  type GridPaginationModel,
} from "@mui/x-data-grid";
import { Link as RouterLink } from "react-router";
import { CompanyAvatar } from "../../components/CompanyAvatar";
import { EmptyState } from "../../components/EmptyState";
import { channelIcons } from "../../components/icons";
import { PriorityBars } from "../../components/PriorityBars";
import { RelativeDate } from "../../components/RelativeDate";
import { StageProgress } from "../../components/StageProgress";
import { StatusChip } from "../../components/StatusChip";
import { Meta, Sep, TwoLineCell } from "../../components/TwoLineCell";
import { useNarrowGrid } from "../../components/useNarrowGrid";
import type { Application } from "./options";

type Props = {
  applications: Application[];
  total: number;
  loading: boolean;
  pagination: GridPaginationModel;
  onPaginationChange: (model: GridPaginationModel) => void;
};

const hideSecondary: GridColumnVisibilityModel = {
  outcome: false,
  progress: false,
  priority: false,
  created_at: false,
};

const columns: GridColDef<Application>[] = [
  {
    field: "role",
    headerName: "Role",
    flex: 2,
    minWidth: 220,
    sortable: false,
    renderCell: ({ row }) => (
      <TwoLineCell
        lead={<CompanyAvatar name={row.company_name} />}
        primary={
          <Link component={RouterLink} to={`/applications/${row.id}`}>
            {row.role}
          </Link>
        }
        secondary={
          <>
            <span>{row.company_name}</span>
            <Sep />
            <Meta icon={channelIcons[row.channel]}>{row.channel}</Meta>
          </>
        }
      />
    ),
  },
  {
    field: "stage",
    headerName: "Stage",
    width: 150,
    sortable: false,
    renderCell: ({ row }) => <StatusChip value={row.stage} />,
  },
  {
    field: "outcome",
    headerName: "Outcome",
    width: 150,
    sortable: false,
    renderCell: ({ row }) => <StatusChip value={row.outcome} />,
  },
  {
    field: "progress",
    headerName: "Progress",
    width: 130,
    sortable: false,
    renderCell: ({ row }) => <StageProgress stage={row.stage} outcome={row.outcome} size="small" />,
  },
  {
    field: "priority",
    headerName: "Priority",
    width: 110,
    sortable: false,
    renderCell: ({ row }) => <PriorityBars value={row.priority} />,
  },
  {
    field: "created_at",
    headerName: "Added",
    width: 120,
    sortable: false,
    renderCell: ({ row }) => <RelativeDate value={row.created_at} />,
  },
];

const NoApplications = () => (
  <EmptyState
    icon={WorkOutlined}
    title="No applications"
    text="Promote an offer from the inbox, or add one with New application."
  />
);

export function ApplicationsGrid({ applications, total, loading, pagination, ...props }: Props) {
  // Below NARROW_GRID_PX of grid width only role and stage are shown.
  const [ref, narrow] = useNarrowGrid();

  return (
    <Box ref={ref}>
      <DataGrid
        rows={applications}
        columns={columns}
        columnVisibilityModel={narrow ? hideSecondary : {}}
        rowHeight={64}
        rowCount={total}
        loading={loading}
        paginationMode="server"
        paginationModel={pagination}
        onPaginationModelChange={props.onPaginationChange}
        pageSizeOptions={[pagination.pageSize]}
        disableColumnMenu
        disableRowSelectionOnClick
        autoHeight
        slots={{ noRowsOverlay: NoApplications }}
      />
    </Box>
  );
}
