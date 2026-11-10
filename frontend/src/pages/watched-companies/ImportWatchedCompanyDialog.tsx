import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
} from "@mui/material";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { api } from "../../api/client";
import { isProblem } from "../../api/problems";
import type { components } from "../../api/schema";
import type { WatchedCompany } from "./WatchedCompaniesPage";

type ImportResult = components["schemas"]["BoardImportRead"];

type Props = { company: WatchedCompany; onClose: () => void };

export function ImportWatchedCompanyDialog({ company, onClose }: Props) {
  const queryClient = useQueryClient();
  const [result, setResult] = useState<ImportResult | null>(null);
  // No fields: the form only tracks the submission and its error.
  const {
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm();

  const onSubmit = handleSubmit(async () => {
    setResult(null);
    const { data, error } = await api.POST(
      "/api/v1/watched-companies/{watched_company_id}/imports",
      { params: { path: { watched_company_id: company.id } } },
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
                {result.found} found, {result.added} added, {result.filtered} filtered,{" "}
                {result.already_in_inbox} already in the inbox, {result.expired} expired
              </Alert>
            )}
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
