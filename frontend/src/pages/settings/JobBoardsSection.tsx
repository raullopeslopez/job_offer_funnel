import CodeOutlined from "@mui/icons-material/CodeOutlined";
import DeleteOutlineOutlined from "@mui/icons-material/DeleteOutlineOutlined";
import EditOutlined from "@mui/icons-material/EditOutlined";
import TravelExploreOutlined from "@mui/icons-material/TravelExploreOutlined";
import { Button, Stack } from "@mui/material";
import { DataGrid, type GridColDef, type GridPaginationModel } from "@mui/x-data-grid";
import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../api/client";
import type { components } from "../../api/schema";
import { EmptyState } from "../../components/EmptyState";
import { IconTile } from "../../components/IconTile";
import { RowAction, RowActions, rowActionsSx } from "../../components/RowActions";
import { Meta, TwoLineCell } from "../../components/TwoLineCell";
import { DeleteJobBoardDialog } from "./DeleteJobBoardDialog";
import { JobBoardDialog } from "./JobBoardDialog";

export type JobBoard = components["schemas"]["JobBoardRead"];

const PAGE_SIZE = 20;

function importedFrom(jobBoard: JobBoard): string {
  if (jobBoard.email_alert) return `${jobBoard.email_alert} alerts`;
  return jobBoard.feed ?? jobBoard.import_method;
}

export function JobBoardsSection() {
  const queryClient = useQueryClient();
  const [pagination, setPagination] = useState<GridPaginationModel>({
    page: 0,
    pageSize: PAGE_SIZE,
  });
  // "new" opens the form empty; a job board opens it to edit that job board.
  const [editing, setEditing] = useState<JobBoard | "new" | null>(null);
  const [deleting, setDeleting] = useState<JobBoard | null>(null);

  const jobBoards = useQuery({
    queryKey: ["job-boards", pagination.page, pagination.pageSize],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/job-boards", {
        params: {
          query: { limit: pagination.pageSize, offset: pagination.page * pagination.pageSize },
        },
      });
      if (error) throw error;
      return data;
    },
    placeholderData: keepPreviousData,
  });

  // The generated searches depend on the job boards.
  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ["job-boards"] });
    await queryClient.invalidateQueries({ queryKey: ["searches"] });
  };

  const columns: GridColDef<JobBoard>[] = [
    {
      field: "name",
      headerName: "Name",
      flex: 1,
      sortable: false,
      renderCell: ({ row }) => (
        <TwoLineCell
          lead={<IconTile icon={TravelExploreOutlined} />}
          primary={row.name}
          secondary={
            <Meta icon={CodeOutlined} mono>
              {row.import_method === "none"
                ? row.syntax
                : `${row.syntax} · imported from ${importedFrom(row)}`}
            </Meta>
          }
        />
      ),
    },
    { field: "search_url_template", headerName: "Search URL template", flex: 2, sortable: false },
    {
      field: "actions",
      headerName: "",
      width: 100,
      sortable: false,
      align: "right",
      renderCell: ({ row }) => (
        <RowActions>
          <RowAction
            icon={EditOutlined}
            label={`Edit “${row.name}”`}
            onClick={() => setEditing(row)}
          />
          <RowAction
            icon={DeleteOutlineOutlined}
            label={`Delete “${row.name}”`}
            onClick={() => setDeleting(row)}
          />
        </RowActions>
      ),
    },
  ];

  return (
    <>
      <Stack direction="row" sx={{ justifyContent: "flex-end", mb: 2 }}>
        <Button variant="contained" onClick={() => setEditing("new")}>
          New job board
        </Button>
      </Stack>

      <DataGrid
        rows={jobBoards.data?.items ?? []}
        columns={columns}
        rowCount={jobBoards.data?.total ?? 0}
        loading={jobBoards.isFetching}
        paginationMode="server"
        paginationModel={pagination}
        onPaginationModelChange={setPagination}
        pageSizeOptions={[pagination.pageSize]}
        disableColumnMenu
        disableRowSelectionOnClick
        autoHeight
        rowHeight={64}
        sx={rowActionsSx}
        slots={{
          noRowsOverlay: () => <EmptyState icon={TravelExploreOutlined} title="No job boards" />,
        }}
      />

      {editing && (
        <JobBoardDialog
          jobBoard={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={async () => {
            setEditing(null);
            await refresh();
          }}
        />
      )}
      <DeleteJobBoardDialog
        jobBoard={deleting}
        onClose={() => setDeleting(null)}
        onDeleted={async () => {
          setDeleting(null);
          await refresh();
        }}
      />
    </>
  );
}
