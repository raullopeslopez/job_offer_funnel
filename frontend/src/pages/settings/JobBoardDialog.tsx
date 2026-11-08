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
import { Controller, useForm } from "react-hook-form";
import { api } from "../../api/client";
import { fieldErrors, isProblem } from "../../api/problems";
import type { components } from "../../api/schema";
import type { JobBoard } from "./JobBoardsSection";

type Syntax = components["schemas"]["Syntax"];
const SYNTAXES: Syntax[] = ["boolean", "minus", "keywords"];

type Values = { name: string; search_url_template: string; syntax: Syntax };
const FIELDS: (keyof Values)[] = ["name", "search_url_template", "syntax"];

/** Creates a job board, or edits `jobBoard` when given. */
type Props = { jobBoard: JobBoard | null; onClose: () => void; onSaved: () => void };

export function JobBoardDialog({ jobBoard, onClose, onSaved }: Props) {
  const {
    register,
    control,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    defaultValues: {
      name: jobBoard?.name ?? "",
      search_url_template: jobBoard?.search_url_template ?? "",
      syntax: jobBoard?.syntax ?? "keywords",
    },
  });

  const onSubmit = handleSubmit(async (body) => {
    const { error } = jobBoard
      ? await api.PATCH("/api/v1/job-boards/{job_board_id}", {
          params: { path: { job_board_id: jobBoard.id } },
          body,
        })
      : await api.POST("/api/v1/job-boards", { body });
    if (!error) {
      onSaved();
      return;
    }
    if (isProblem(error, "already-exists")) {
      setError("root", { message: "The job board already exists" });
      return;
    }
    const byField = fieldErrors(error);
    for (const field of FIELDS) {
      const message = byField[field];
      if (message) setError(field, { message });
    }
    if (Object.keys(byField).length === 0) {
      setError("root", { message: error.title });
    }
  });

  return (
    <Dialog open onClose={onClose} fullWidth>
      <form onSubmit={onSubmit} noValidate>
        <DialogTitle>{jobBoard ? `Edit “${jobBoard.name}”` : "New job board"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {errors.root && <Alert severity="error">{errors.root.message}</Alert>}
            <TextField
              {...register("name")}
              label="Name"
              fullWidth
              error={Boolean(errors.name)}
              helperText={errors.name?.message}
            />
            <TextField
              {...register("search_url_template")}
              label="Search URL template"
              fullWidth
              error={Boolean(errors.search_url_template)}
              helperText={
                errors.search_url_template?.message ??
                "{query} marks the search; {location} is optional"
              }
            />
            <Controller
              name="syntax"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  select
                  label="Syntax"
                  fullWidth
                  error={Boolean(errors.syntax)}
                  helperText={errors.syntax?.message}
                >
                  {SYNTAXES.map((syntax) => (
                    <MenuItem key={syntax} value={syntax}>
                      {syntax}
                    </MenuItem>
                  ))}
                </TextField>
              )}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" loading={isSubmitting}>
            {jobBoard ? "Save" : "Create"}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
