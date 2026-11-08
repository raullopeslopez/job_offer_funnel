import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  TextField,
} from "@mui/material";
import { useForm } from "react-hook-form";
import { api } from "../../api/client";
import { fieldErrors, isProblem } from "../../api/problems";
import type { Company } from "./CompaniesSection";

type Values = { name: string; website: string };
const FIELDS: (keyof Values)[] = ["name", "website"];

/** Creates a company, or edits `company` when given. */
type Props = { company: Company | null; onClose: () => void; onSaved: () => void };

export function CompanyDialog({ company, onClose, onSaved }: Props) {
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    defaultValues: { name: company?.name ?? "", website: company?.website ?? "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    const body = { name: values.name, website: values.website || null };
    const { error } = company
      ? await api.PATCH("/api/v1/companies/{company_id}", {
          params: { path: { company_id: company.id } },
          body,
        })
      : await api.POST("/api/v1/companies", { body });
    if (!error) {
      onSaved();
      return;
    }
    if (isProblem(error, "already-exists")) {
      setError("root", { message: "The company already exists" });
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
        <DialogTitle>{company ? `Edit “${company.name}”` : "New company"}</DialogTitle>
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
              {...register("website")}
              label="Website"
              fullWidth
              error={Boolean(errors.website)}
              helperText={errors.website?.message}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" loading={isSubmitting}>
            {company ? "Save" : "Create"}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
