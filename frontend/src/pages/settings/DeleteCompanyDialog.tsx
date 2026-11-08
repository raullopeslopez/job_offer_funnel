import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from "@mui/material";
import { useMutation } from "@tanstack/react-query";
import { api } from "../../api/client";
import { isProblem } from "../../api/problems";
import type { Company } from "./CompaniesSection";

type Props = { company: Company | null; onClose: () => void; onDeleted: () => void };

export function DeleteCompanyDialog({ company, onClose, onDeleted }: Props) {
  const remove = useMutation({
    mutationFn: async (companyId: string) => {
      const { error } = await api.DELETE("/api/v1/companies/{company_id}", {
        params: { path: { company_id: companyId } },
      });
      if (error) throw error;
    },
    onSuccess: onDeleted,
  });

  const close = () => {
    remove.reset();
    onClose();
  };

  return (
    <Dialog open={company !== null} onClose={close} fullWidth>
      <DialogTitle>Delete “{company?.name}”?</DialogTitle>
      <DialogContent>
        {remove.error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {isProblem(remove.error, "in-use")
              ? "The company has applications and cannot be deleted"
              : "Could not delete the company"}
          </Alert>
        )}
        <DialogContentText>Only a company without applications can be deleted.</DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={close}>Cancel</Button>
        <Button
          variant="contained"
          color="error"
          loading={remove.isPending}
          onClick={() => company && remove.mutate(company.id)}
        >
          Delete
        </Button>
      </DialogActions>
    </Dialog>
  );
}
