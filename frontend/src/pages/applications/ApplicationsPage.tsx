import { Button, MenuItem, Stack, TextField, Typography } from "@mui/material";
import type { GridPaginationModel } from "@mui/x-data-grid";
import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useSearchParams } from "react-router";
import { api } from "../../api/client";
import { ApplicationDialog } from "./ApplicationDialog";
import { ApplicationsGrid } from "./ApplicationsGrid";
import { CHANNELS, type Channel, OUTCOMES, type Outcome, STAGES, type Stage } from "./options";

const PAGE_SIZE = 20;
const STATUSES = ["active", "closed"] as const;

// Each filter lives in the URL; an empty value means "any".
const FILTERS = [
  { name: "stage", label: "Stage", values: STAGES },
  { name: "outcome", label: "Outcome", values: OUTCOMES },
  { name: "channel", label: "Channel", values: CHANNELS },
  { name: "status", label: "Status", values: STATUSES },
] as const;

export function ApplicationsPage() {
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const [pagination, setPagination] = useState<GridPaginationModel>({
    page: 0,
    pageSize: PAGE_SIZE,
  });
  const [creating, setCreating] = useState(false);

  const status = params.get("status");
  const query = {
    stage: (params.get("stage") as Stage | null) ?? undefined,
    outcome: (params.get("outcome") as Outcome | null) ?? undefined,
    channel: (params.get("channel") as Channel | null) ?? undefined,
    active: status === "active" ? true : status === "closed" ? false : undefined,
  };

  const applications = useQuery({
    queryKey: ["applications", query, pagination.page, pagination.pageSize],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/applications", {
        params: {
          query: {
            ...query,
            limit: pagination.pageSize,
            offset: pagination.page * pagination.pageSize,
          },
        },
      });
      if (error) throw error;
      return data;
    },
    placeholderData: keepPreviousData,
  });

  const changeFilter = (name: string, value: string) => {
    setParams((current) => {
      const next = new URLSearchParams(current);
      if (value) next.set(name, value);
      else next.delete(name);
      return next;
    });
    setPagination((current) => ({ ...current, page: 0 }));
  };

  const total = applications.data?.total ?? 0;

  return (
    <>
      <Stack direction="row" sx={{ alignItems: "center", mb: 2 }}>
        <Typography variant="h4" component="h1" sx={{ flexGrow: 1 }}>
          Applications
        </Typography>
        <Button variant="contained" onClick={() => setCreating(true)}>
          New application
        </Button>
      </Stack>

      <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
        {FILTERS.map(({ name, label, values }) => (
          <TextField
            key={name}
            select
            size="small"
            label={label}
            value={params.get(name) ?? ""}
            onChange={(event) => changeFilter(name, event.target.value)}
            slotProps={{ select: { displayEmpty: true }, inputLabel: { shrink: true } }}
            sx={{ minWidth: 160 }}
          >
            <MenuItem value="">Any</MenuItem>
            {values.map((value) => (
              <MenuItem key={value} value={value}>
                {value}
              </MenuItem>
            ))}
          </TextField>
        ))}
      </Stack>

      <Typography color="text.secondary" sx={{ mb: 1 }}>
        {total === 1 ? "1 application" : `${total} applications`}
      </Typography>

      <ApplicationsGrid
        applications={applications.data?.items ?? []}
        total={total}
        loading={applications.isFetching}
        pagination={pagination}
        onPaginationChange={setPagination}
      />

      {creating && (
        <ApplicationDialog
          application={null}
          onClose={() => setCreating(false)}
          onSaved={async () => {
            setCreating(false);
            await queryClient.invalidateQueries({ queryKey: ["applications"] });
          }}
        />
      )}
    </>
  );
}
