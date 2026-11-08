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
import { fieldErrors } from "../../api/problems";
import { type Application, OUTCOMES, type Outcome, STAGES, type Stage } from "./options";

// Empty strings stand for "not set"; the API receives them as null.
type Values = { target: Stage | Outcome | ""; occurred_on: string; note: string };

/** Moves `application` to a stage or closes it with an outcome; the API decides what is allowed. */
type Props = {
  application: Application;
  mode: "move" | "close";
  onClose: () => void;
  onSaved: () => void;
};

export function TransitionDialog({ application, mode, onClose, onSaved }: Props) {
  const {
    register,
    control,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ defaultValues: { target: "", occurred_on: "", note: "" } });
  const moving = mode === "move";
  const targetField = moving ? "to_stage" : "outcome";

  const onSubmit = handleSubmit(async (values) => {
    const target = values.target || null;
    const { error } = await api.POST("/api/v1/applications/{application_id}/transitions", {
      params: { path: { application_id: application.id } },
      body: {
        ...(moving ? { to_stage: target as Stage | null } : { outcome: target as Outcome | null }),
        occurred_on: values.occurred_on || null,
        note: values.note || null,
      },
    });
    if (!error) {
      onSaved();
      return;
    }
    const byField = fieldErrors(error);
    const messages: [keyof Values, string | undefined][] = [
      ["target", byField[targetField]],
      ["occurred_on", byField.occurred_on],
      ["note", byField.note],
    ];
    let shown = false;
    for (const [field, message] of messages) {
      if (message) {
        setError(field, { message });
        shown = true;
      }
    }
    // Rejected by the funnel (409) or not tied to a field: the API's message, as is.
    if (!shown) setError("root", { message: error.detail ?? error.title });
  });

  const label = moving ? "Stage" : "Outcome";
  return (
    <Dialog open onClose={onClose} fullWidth>
      <form onSubmit={onSubmit} noValidate>
        <DialogTitle>
          {moving ? `Move “${application.role}”` : `Close “${application.role}”`}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {errors.root && <Alert severity="error">{errors.root.message}</Alert>}
            <Controller
              name="target"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  select
                  label={label}
                  fullWidth
                  error={Boolean(errors.target)}
                  helperText={errors.target?.message}
                >
                  {(moving ? STAGES : OUTCOMES).map((value) => (
                    <MenuItem key={value} value={value}>
                      {value}
                    </MenuItem>
                  ))}
                </TextField>
              )}
            />
            <TextField
              {...register("occurred_on")}
              type="date"
              label="Date"
              fullWidth
              slotProps={{ inputLabel: { shrink: true } }}
              error={Boolean(errors.occurred_on)}
              helperText={errors.occurred_on?.message ?? "Empty means today"}
            />
            <TextField
              {...register("note")}
              label="Note"
              fullWidth
              multiline
              minRows={2}
              error={Boolean(errors.note)}
              helperText={errors.note?.message}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" loading={isSubmitting}>
            {moving ? "Move" : "Close"}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
