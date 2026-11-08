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

type Ats = components["schemas"]["Ats"];
const ATS_OPTIONS: Ats[] = ["greenhouse", "lever", "ashby"];

type Values = { name: string; ats: Ats; board: string };
const FIELDS: (keyof Values)[] = ["name", "ats", "board"];

type Props = { onClose: () => void; onWatched: () => void };

export function WatchCompanyDialog({ onClose, onWatched }: Props) {
  const {
    register,
    control,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ defaultValues: { name: "", ats: "greenhouse", board: "" } });

  const onSubmit = handleSubmit(async (body) => {
    const { error } = await api.POST("/api/v1/watched-companies", { body });
    if (!error) {
      onWatched();
      return;
    }
    if (isProblem(error, "already-exists")) {
      setError("root", { message: error.detail ?? error.title });
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
        <DialogTitle>Watch a company</DialogTitle>
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
            <Controller
              name="ats"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  select
                  label="ATS"
                  fullWidth
                  error={Boolean(errors.ats)}
                  helperText={errors.ats?.message}
                >
                  {ATS_OPTIONS.map((ats) => (
                    <MenuItem key={ats} value={ats}>
                      {ats}
                    </MenuItem>
                  ))}
                </TextField>
              )}
            />
            <TextField
              {...register("board")}
              label="Board"
              fullWidth
              error={Boolean(errors.board)}
              helperText={
                errors.board?.message ??
                "The company's name in its careers URL, e.g. boards.greenhouse.io/acme"
              }
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" loading={isSubmitting}>
            Watch
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
