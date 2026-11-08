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
import type { WatchedCompany } from "./WatchedCompaniesPage";

type ImportResult = components["schemas"]["BoardImportRead"];
type Values = { profile_id: string };

type Props = { company: WatchedCompany; onClose: () => void };

export function ImportWatchedCompanyDialog({ company, onClose }: Props) {
  const queryClient = useQueryClient();
  const [result, setResult] = useState<ImportResult | null>(null);
  const {
    control,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ defaultValues: { profile_id: "" } });

  const profiles = useQuery({
    queryKey: ["search-profiles"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/search-profiles", {
        params: { query: { limit: 100 } },
      });
      if (error) throw error;
      return data.items;
    },
  });

  const onSubmit = handleSubmit(async ({ profile_id }) => {
    if (!profile_id) {
      setError("profile_id", { message: "Choose a search profile" });
      return;
    }
    setResult(null);
    const { data, error } = await api.POST(
      "/api/v1/watched-companies/{watched_company_id}/imports",
      { params: { path: { watched_company_id: company.id } }, body: { profile_id } },
    );
    if (data) {
      setResult(data);
      await queryClient.invalidateQueries({ queryKey: ["offers"] });
    } else if (isProblem(error, "board-unavailable")) {
      setError("root", {
        message: `Board not available: check the ATS and the board of ${company.name}, or try again later.`,
      });
    } else {
      setError("root", { message: error?.title ?? "The API returned an unexpected error" });
    }
  });

  return (
    <Dialog open onClose={onClose} fullWidth>
      <form onSubmit={onSubmit} noValidate>
        <DialogTitle>Import “{company.name}”</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {errors.root && <Alert severity="warning">{errors.root.message}</Alert>}
            {result && (
              <Alert severity="success">
                {result.found} found, {result.matching} matching, {result.added} added,{" "}
                {result.already_in_inbox} already in the inbox, {result.expired} expired
              </Alert>
            )}
            <Controller
              name="profile_id"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  select
                  label="Search profile"
                  fullWidth
                  error={Boolean(errors.profile_id)}
                  helperText={errors.profile_id?.message}
                >
                  {(profiles.data ?? []).map((profile) => (
                    <MenuItem key={profile.id} value={profile.id}>
                      {profile.name}
                    </MenuItem>
                  ))}
                </TextField>
              )}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Close</Button>
          <Button type="submit" variant="contained" loading={isSubmitting}>
            Import
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
