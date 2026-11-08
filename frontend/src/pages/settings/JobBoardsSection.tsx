import { Button, Stack } from "@mui/material";
import { DataGrid, type GridColDef, type GridPaginationModel } from "@mui/x-data-grid";
import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../api/client";
import type { components } from "../../api/schema";
import { DeleteJobBoardDialog } from "./DeleteJobBoardDialog";
import { JobBoardDialog } from "./JobBoardDialog";

export type JobBoard = components["schemas"]["JobBoardRead"];

const PAGE_SIZE = 20;

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
    { field: "name", headerName: "Name", flex: 1, sortable: false },
    { field: "search_url_template", headerName: "Search URL template", flex: 3, sortable: false },
    { field: "syntax", headerName: "Syntax", flex: 1, sortable: false },
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
        localeText={{ noRowsLabel: "No job boards" }}
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
