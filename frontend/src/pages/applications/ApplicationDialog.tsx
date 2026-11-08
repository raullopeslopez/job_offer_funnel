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
import { type Application, CHANNELS, type Channel, PRIORITIES, type Priority } from "./options";

type FirstStage = "evaluated" | "applied";
const FIRST_STAGES: FirstStage[] = ["evaluated", "applied"];

// Empty strings stand for "not set"; the API receives them as null.
type Values = {
  company_id: string;
  role: string;
  channel: Channel;
  priority: Priority | "";
  url: string;
  notes: string;
  stage: FirstStage;
  occurred_on: string;
};
const FIELDS: (keyof Values)[] = [
  "company_id",
  "role",
  "channel",
  "priority",
  "url",
  "notes",
  "stage",
  "occurred_on",
];

function toValues(application: Application | null): Values {
  return {
    company_id: application?.company_id ?? "",
    role: application?.role ?? "",
    channel: application?.channel ?? "portal",
    priority: application?.priority ?? "",
    url: application?.url ?? "",
    notes: application?.notes ?? "",
    stage: "evaluated",
    occurred_on: "",
  };
}

/** Creates an application, or edits `application` when given (its stage is not edited here). */
type Props = { application: Application | null; onClose: () => void; onSaved: () => void };

export function ApplicationDialog({ application, onClose, onSaved }: Props) {
  const {
    register,
    control,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ defaultValues: toValues(application) });

  const companies = useQuery({
    queryKey: ["companies", "options"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/companies", {
        params: { query: { limit: 100 } },
      });
      if (error) throw error;
      return data.items;
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    const fields = {
      company_id: values.company_id,
      role: values.role,
      channel: values.channel,
      priority: values.priority || null,
      url: values.url || null,
      notes: values.notes || null,
    };
    const { error } = application
      ? await api.PATCH("/api/v1/applications/{application_id}", {
          params: { path: { application_id: application.id } },
          body: fields,
        })
      : await api.POST("/api/v1/applications", {
          body: { ...fields, stage: values.stage, occurred_on: values.occurred_on || null },
        });
    if (!error) {
      onSaved();
      return;
    }
    if (isProblem(error, "unknown-company")) {
      setError("company_id", { message: "The company does not exist" });
      return;
    }
    if (isProblem(error, "invalid-transition-date")) {
      setError("occurred_on", { message: "The date cannot be in the future" });
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

  const select = <Name extends "company_id" | "channel" | "priority" | "stage">(
    name: Name,
    label: string,
    options: { value: string; label: string }[],
  ) => (
    <Controller
      name={name}
      control={control}
      render={({ field }) => (
        <TextField
          {...field}
          select
          label={label}
          fullWidth
          error={Boolean(errors[name])}
          helperText={errors[name]?.message}
        >
          {options.map((option) => (
            <MenuItem key={option.value} value={option.value}>
              {option.label}
            </MenuItem>
          ))}
        </TextField>
      )}
    />
  );
  const asOptions = (values: string[]) => values.map((value) => ({ value, label: value }));

  const textField = (name: "role" | "url" | "notes", label: string, multiline = false) => (
    <TextField
      {...register(name)}
      label={label}
      fullWidth
      multiline={multiline}
      minRows={multiline ? 3 : undefined}
      error={Boolean(errors[name])}
      helperText={errors[name]?.message}
    />
  );

  return (
    <Dialog open onClose={onClose} fullWidth>
      <form onSubmit={onSubmit} noValidate>
        <DialogTitle>{application ? `Edit “${application.role}”` : "New application"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {errors.root && <Alert severity="error">{errors.root.message}</Alert>}
            {select(
              "company_id",
              "Company",
              (companies.data ?? []).map(({ id, name }) => ({ value: id, label: name })),
            )}
            {textField("role", "Role")}
            {select("channel", "Channel", asOptions(CHANNELS))}
            {select("priority", "Priority", [
              { value: "", label: "None" },
              ...asOptions(PRIORITIES),
            ])}
            {textField("url", "URL")}
            {textField("notes", "Notes", true)}
            {!application && select("stage", "Stage", asOptions(FIRST_STAGES))}
            {!application && (
              <TextField
                {...register("occurred_on")}
                type="date"
                label="Start date"
                fullWidth
                slotProps={{ inputLabel: { shrink: true } }}
                error={Boolean(errors.occurred_on)}
                helperText={
                  errors.occurred_on?.message ?? "When it entered that stage; empty means today"
                }
              />
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" loading={isSubmitting}>
            {application ? "Save" : "Create"}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
