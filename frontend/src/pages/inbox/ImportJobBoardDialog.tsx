import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Stack,
  TextField,
} from "@mui/material";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { api } from "../../api/client";
import { isProblem } from "../../api/problems";
import type { components } from "../../api/schema";

type ImportResult = components["schemas"]["ImportRead"];
type Values = { job_board_id: string };

// The API's largest page: more job boards than this would need paging.
const PAGE_LIMIT = 100;

const relative = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

/** "in 5 hours" / "in 20 minutes", from the Retry-After seconds of a 429. */
function inTime(seconds: number): string {
  const minutes = Math.ceil(seconds / 60);
  return minutes >= 60
    ? relative.format(Math.round(minutes / 60), "hour")
    : relative.format(minutes, "minute");
}

type Props = { open: boolean; onClose: () => void };

export function ImportJobBoardDialog({ open, onClose }: Props) {
  const queryClient = useQueryClient();
  const [result, setResult] = useState<ImportResult | null>(null);
  const {
    control,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ defaultValues: { job_board_id: "" } });

  // Only the job boards with an import method can be imported.
  const jobBoards = useQuery({
    queryKey: ["job-boards", "imported"],
    enabled: open,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/job-boards", {
        params: { query: { limit: PAGE_LIMIT } },
      });
      if (error) throw error;
      // Email job boards are imported as their alerts arrive, not on demand.
      return data.items.filter(
        ({ import_method }) => import_method === "api" || import_method === "rss",
      );
    },
  });
  const close = () => {
    reset();
    setResult(null);
    onClose();
  };

  const onSubmit = handleSubmit(async ({ job_board_id }) => {
    const name = jobBoards.data?.find((jobBoard) => jobBoard.id === job_board_id)?.name;
    if (!name) {
      setError("job_board_id", { message: "Choose a job board" });
      return;
    }
    setResult(null);
    const { data, error, response } = await api.POST("/api/v1/job-boards/{job_board_id}/imports", {
      params: { path: { job_board_id } },
    });
    if (data) {
      setResult(data);
      await queryClient.invalidateQueries({ queryKey: ["offers"] });
      await queryClient.invalidateQueries({ queryKey: ["job-boards"] });
    } else if (isProblem(error, "feed-cooldown")) {
      const wait = Number(response.headers.get("Retry-After") ?? 0);
      setError("root", { message: `${name} can be imported again ${inTime(wait)}` });
    } else if (isProblem(error, "feed-unavailable")) {
      setError("root", { message: `${name} is not available right now. Try again later.` });
    } else {
      setError("root", { message: error?.title ?? "The API returned an unexpected error" });
    }
  });

  return (
    <Dialog open={open} onClose={close} fullWidth>
      <form onSubmit={onSubmit} noValidate>
        <DialogTitle>Import job board</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {errors.root && <Alert severity="warning">{errors.root.message}</Alert>}
            {result && (
              <Alert severity="success">
                {result.found} found, {result.added} added, {result.filtered} filtered,{" "}
                {result.already_in_inbox} already in the inbox, {result.expired} expired
              </Alert>
            )}
            <Controller
              name="job_board_id"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  select
                  label="Job board"
                  fullWidth
                  error={Boolean(errors.job_board_id)}
                  helperText={errors.job_board_id?.message}
                >
                  {(jobBoards.data ?? []).map(({ id, name }) => (
                    <MenuItem key={id} value={id}>
                      {name}
                    </MenuItem>
                  ))}
                </TextField>
              )}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={close}>Close</Button>
          <Button type="submit" variant="contained" loading={isSubmitting}>
            Import
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
