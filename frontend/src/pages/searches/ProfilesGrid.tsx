import DeleteOutlineOutlined from "@mui/icons-material/DeleteOutlineOutlined";
import EditOutlined from "@mui/icons-material/EditOutlined";
import ManageSearchOutlined from "@mui/icons-material/ManageSearchOutlined";
import PlaceOutlined from "@mui/icons-material/PlaceOutlined";
import { Box, Button, Stack } from "@mui/material";
import { DataGrid, type GridColDef, type GridPaginationModel } from "@mui/x-data-grid";
import type { components } from "../../api/schema";
import { EmptyState } from "../../components/EmptyState";
import { IconTile } from "../../components/IconTile";
import { RowAction, RowActions, rowActionsSx } from "../../components/RowActions";
import { Meta, Sep, TwoLineCell } from "../../components/TwoLineCell";
import { useNarrowGrid } from "../../components/useNarrowGrid";
import { Tokens } from "./Tokens";

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

// Below NARROW_GRID_PX of grid width only the name and the actions are shown.
const hideSecondary = { titles: false, keywords: false, excluded_keywords: false };

export function ProfilesGrid({ profiles, total, loading, pagination, ...props }: Props) {
  const [ref, narrow] = useNarrowGrid();
  const columns: GridColDef<Profile>[] = [
    {
      field: "name",
      headerName: "Name",
      flex: 1.6,
      sortable: false,
      renderCell: ({ row }) => (
        <TwoLineCell
          lead={<IconTile icon={ManageSearchOutlined} />}
          primary={row.name}
          secondary={
            <>
              <Meta icon={PlaceOutlined}>{row.location || "—"}</Meta>
              {row.work_modes.length > 0 && (
                <>
                  <Sep />
                  <Meta>{joined(row.work_modes)}</Meta>
                </>
              )}
            </>
          }
        />
      ),
    },
    { field: "titles", headerName: "Titles", flex: 2, sortable: false, valueFormatter: joined },
    {
      field: "keywords",
      headerName: "Keywords",
      flex: 1,
      sortable: false,
      renderCell: ({ row }) => <Tokens items={row.keywords} />,
    },
    {
      field: "excluded_keywords",
      headerName: "Excluded",
      flex: 1,
      sortable: false,
      renderCell: ({ row }) => <Tokens items={row.excluded_keywords} excluded />,
    },
    {
      field: "actions",
      headerName: "",
      width: 200,
      sortable: false,
      renderCell: ({ row }) => (
        <Stack direction="row" spacing={0.5} sx={{ height: "100%", alignItems: "center" }}>
          <Button size="small" onClick={() => props.onSearches(row)}>
            Searches
          </Button>
          <RowActions>
            <RowAction
              icon={EditOutlined}
              label={`Edit “${row.name}”`}
              onClick={() => props.onEdit(row)}
            />
            <RowAction
              icon={DeleteOutlineOutlined}
              label={`Delete “${row.name}”`}
              onClick={() => props.onDelete(row)}
            />
          </RowActions>
        </Stack>
      ),
    },
  ];

  return (
    <Box ref={ref}>
      <DataGrid
        rows={profiles}
        columns={columns}
        columnVisibilityModel={narrow ? hideSecondary : {}}
        rowCount={total}
        loading={loading}
        paginationMode="server"
        paginationModel={pagination}
        onPaginationModelChange={props.onPaginationChange}
        pageSizeOptions={[pagination.pageSize]}
        disableColumnMenu
        disableRowSelectionOnClick
        autoHeight
        rowHeight={64}
        sx={rowActionsSx}
        slots={{
          noRowsOverlay: () => (
            <EmptyState
              icon={ManageSearchOutlined}
              title="No profiles"
              text="A profile turns titles and keywords into a search for every job board."
            />
          ),
        }}
      />
    </Box>
  );
}
