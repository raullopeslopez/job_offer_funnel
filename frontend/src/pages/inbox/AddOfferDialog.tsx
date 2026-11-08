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
import { useQuery } from "@tanstack/react-query";
import { Controller, useForm } from "react-hook-form";
import { api } from "../../api/client";
import { fieldErrors, isProblem } from "../../api/problems";

type Values = { url: string; company: string; title: string; job_board_id: string; notes: string };
const EMPTY: Values = { url: "", company: "", title: "", job_board_id: "", notes: "" };
const FIELDS = Object.keys(EMPTY) as (keyof Values)[];

type Props = { open: boolean; onClose: () => void; onAdded: () => void };

export function AddOfferDialog({ open, onClose, onAdded }: Props) {
  const {
    register,
    control,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ defaultValues: EMPTY });

  const jobBoards = useQuery({
    queryKey: ["job-boards"],
    enabled: open,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/job-boards", {
        params: { query: { limit: 100 } },
      });
      if (error) throw error;
      return data.items;
    },
  });

  const close = () => {
    reset(EMPTY);
    onClose();
  };

  const onSubmit = handleSubmit(async ({ job_board_id, notes, ...offer }) => {
    const { error } = await api.POST("/api/v1/offers", {
      body: { ...offer, job_board_id: job_board_id || null, notes: notes || null },
    });
    if (!error) {
      reset(EMPTY);
      onAdded();
      return;
    }
    if (isProblem(error, "already-exists")) {
      setError("root", { message: "The offer already exists" });
    } else if (isProblem(error, "unknown-job-board")) {
      setError("job_board_id", { message: "The job board does not exist" });
    } else {
      const byField = fieldErrors(error);
      for (const field of FIELDS) {
        const message = byField[field];
        if (message) setError(field, { message });
      }
      if (Object.keys(byField).length === 0) {
        setError("root", { message: "The API returned an unexpected error" });
      }
    }
  });

  const textField = (name: keyof Values, label: string) => (
    <TextField
      {...register(name)}
      label={label}
      fullWidth
      error={Boolean(errors[name])}
      helperText={errors[name]?.message}
    />
  );

  return (
    <Dialog open={open} onClose={close} fullWidth>
      <form onSubmit={onSubmit} noValidate>
        <DialogTitle>Add offer</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {errors.root && <Alert severity="error">{errors.root.message}</Alert>}
            {textField("url", "URL")}
            {textField("company", "Company")}
            {textField("title", "Title")}
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
                  <MenuItem value="">None</MenuItem>
                  {(jobBoards.data ?? []).map((board) => (
                    <MenuItem key={board.id} value={board.id}>
                      {board.name}
                    </MenuItem>
                  ))}
                </TextField>
              )}
            />
            <TextField
              {...register("notes")}
              label="Notes"
              fullWidth
              multiline
              minRows={2}
              error={Boolean(errors.notes)}
              helperText={errors.notes?.message}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={close}>Cancel</Button>
          <Button type="submit" variant="contained" loading={isSubmitting}>
            Add
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
