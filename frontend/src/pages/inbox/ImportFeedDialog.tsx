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

type Feed = components["schemas"]["Feed"];
type ImportResult = components["schemas"]["ImportRead"];
type Values = { feed: Feed | "" };

const relative = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

/** "in 5 hours" / "in 20 minutes", from the Retry-After seconds of a 429. */
function inTime(seconds: number): string {
  const minutes = Math.ceil(seconds / 60);
  return minutes >= 60
    ? relative.format(Math.round(minutes / 60), "hour")
    : relative.format(minutes, "minute");
}

type Props = { open: boolean; onClose: () => void };

export function ImportFeedDialog({ open, onClose }: Props) {
  const queryClient = useQueryClient();
  const [result, setResult] = useState<ImportResult | null>(null);
  const {
    control,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ defaultValues: { feed: "" } });

  const feeds = useQuery({
    queryKey: ["feeds"],
    enabled: open,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/feeds");
      if (error) throw error;
      return data;
    },
  });
  const close = () => {
    reset();
    setResult(null);
    onClose();
  };

  const onSubmit = handleSubmit(async ({ feed }) => {
    if (!feed) {
      setError("feed", { message: "Choose a feed" });
      return;
    }
    setResult(null);
    const { data, error, response } = await api.POST("/api/v1/feeds/{feed}/imports", {
      params: { path: { feed } },
    });
    if (data) {
      setResult(data);
      await queryClient.invalidateQueries({ queryKey: ["offers"] });
      await queryClient.invalidateQueries({ queryKey: ["feeds"] });
    } else if (isProblem(error, "feed-cooldown")) {
      const wait = Number(response.headers.get("Retry-After") ?? 0);
      setError("root", { message: `${feed} can be imported again ${inTime(wait)}` });
    } else if (isProblem(error, "feed-unavailable")) {
      setError("root", { message: `${feed} is not available right now. Try again later.` });
    } else {
      setError("root", { message: error?.title ?? "The API returned an unexpected error" });
    }
  });

  return (
    <Dialog open={open} onClose={close} fullWidth>
      <form onSubmit={onSubmit} noValidate>
        <DialogTitle>Import feed</DialogTitle>
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
              name="feed"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  select
                  label="Feed"
                  fullWidth
                  error={Boolean(errors.feed)}
                  helperText={errors.feed?.message}
                >
                  {(feeds.data ?? []).map(({ feed }) => (
                    <MenuItem key={feed} value={feed}>
                      {feed}
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
