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
import type { Profile } from "./ProfilesGrid";

type WorkMode = components["schemas"]["WorkMode"];
const WORK_MODES: WorkMode[] = ["remote", "hybrid", "onsite"];

// The lists are typed as comma-separated text; the API trims and validates each item.
type Values = {
  name: string;
  titles: string;
  keywords: string;
  excluded_keywords: string;
  location: string;
  work_modes: WorkMode[];
};
const FIELDS: (keyof Values)[] = [
  "name",
  "titles",
  "keywords",
  "excluded_keywords",
  "location",
  "work_modes",
];

const toList = (text: string) => (text.trim() === "" ? [] : text.split(","));

function toValues(profile: Profile | null): Values {
  return {
    name: profile?.name ?? "",
    titles: profile?.titles.join(", ") ?? "",
    keywords: profile?.keywords.join(", ") ?? "",
    excluded_keywords: profile?.excluded_keywords.join(", ") ?? "",
    location: profile?.location ?? "",
    work_modes: profile?.work_modes ?? [],
  };
}

/** Creates a profile, or edits `profile` when given. */
type Props = { profile: Profile | null; onClose: () => void; onSaved: () => void };

export function ProfileDialog({ profile, onClose, onSaved }: Props) {
  const {
    register,
    control,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ defaultValues: toValues(profile) });

  const onSubmit = handleSubmit(async (values) => {
    const body = {
      name: values.name,
      titles: toList(values.titles),
      keywords: toList(values.keywords),
      excluded_keywords: toList(values.excluded_keywords),
      location: values.location || null,
      work_modes: values.work_modes,
    };
    const { error } = profile
      ? await api.PATCH("/api/v1/search-profiles/{profile_id}", {
          params: { path: { profile_id: profile.id } },
          body,
        })
      : await api.POST("/api/v1/search-profiles", { body });
    if (!error) {
      onSaved();
      return;
    }
    if (isProblem(error, "already-exists")) {
      setError("root", { message: "The search profile already exists" });
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

  const textField = (name: Exclude<keyof Values, "work_modes">, label: string, hint?: string) => (
    <TextField
      {...register(name)}
      label={label}
      fullWidth
      error={Boolean(errors[name])}
      helperText={errors[name]?.message ?? hint}
    />
  );

  return (
    <Dialog open onClose={onClose} fullWidth>
      <form onSubmit={onSubmit} noValidate>
        <DialogTitle>{profile ? `Edit “${profile.name}”` : "New profile"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {errors.root && <Alert severity="error">{errors.root.message}</Alert>}
            {textField("name", "Name")}
            {textField("titles", "Titles", "Separated by commas; any of them may match")}
            {textField("keywords", "Keywords", "Separated by commas; all of them must appear")}
            {textField(
              "excluded_keywords",
              "Excluded keywords",
              "Separated by commas; none of them may appear",
            )}
            {textField("location", "Location")}
            <Controller
              name="work_modes"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  select
                  label="Work modes"
                  fullWidth
                  slotProps={{ select: { multiple: true } }}
                  error={Boolean(errors.work_modes)}
                  helperText={errors.work_modes?.message ?? "None means any"}
                >
                  {WORK_MODES.map((mode) => (
                    <MenuItem key={mode} value={mode}>
                      {mode}
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
            {profile ? "Save" : "Create"}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
