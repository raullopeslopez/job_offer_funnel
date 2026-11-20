import WorkOutlined from "@mui/icons-material/WorkOutlined";
import { Box, Link, Stack, type Theme, useMediaQuery } from "@mui/material";
import {
  DataGrid,
  type GridColDef,
  type GridColumnVisibilityModel,
  type GridPaginationModel,
} from "@mui/x-data-grid";
import { Link as RouterLink } from "react-router";
import { CardList } from "../../components/CardList";
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

/** One application on a phone: the same as its row, with nothing cut. */
function ApplicationCard({ application: row }: { application: Application }) {
  return (
    <Stack spacing={1.25}>
      <Box sx={{ display: "flex", gap: 1.5, alignItems: "flex-start" }}>
        <CompanyAvatar name={row.company_name} />
        <Box sx={{ minWidth: 0 }}>
          <Link component={RouterLink} to={`/applications/${row.id}`} sx={{ fontWeight: 500 }}>
            {row.role}
          </Link>
          <Box
            sx={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              gap: "6px",
              typography: "caption",
              color: "text.secondary",
            }}
          >
            <span>{row.company_name}</span>
            <Sep />
            <Meta icon={channelIcons[row.channel]}>{row.channel}</Meta>
          </Box>
        </Box>
      </Box>
      <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 1.5 }}>
        <StatusChip value={row.stage} />
        {row.outcome && <StatusChip value={row.outcome} />}
        <StageProgress stage={row.stage} outcome={row.outcome} size="small" />
        <PriorityBars value={row.priority} />
        <Box sx={{ ml: "auto", typography: "caption", color: "text.secondary" }}>
          <RelativeDate value={row.created_at} />
        </Box>
      </Box>
    </Stack>
  );
}

export function ApplicationsGrid({ applications, total, loading, pagination, ...props }: Props) {
  // Below NARROW_GRID_PX of grid width only role and stage are shown; on a phone, cards.
  const [ref, narrow] = useNarrowGrid();
  const isPhone = useMediaQuery((theme: Theme) => theme.breakpoints.down("sm"));

  if (isPhone) {
    return (
      <CardList
        aria-label="Applications"
        rows={applications}
        rowKey={(row) => row.id}
        renderCard={(row) => <ApplicationCard application={row} />}
        total={total}
        loading={loading}
        pagination={pagination}
        onPaginationChange={props.onPaginationChange}
        empty={<NoApplications />}
      />
    );
  }

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
