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
import type { Application } from "./options";

type Props = { application: Application; onClose: () => void; onDeleted: () => void };

export function DeleteApplicationDialog({ application, onClose, onDeleted }: Props) {
  const remove = useMutation({
    mutationFn: async () => {
      const { error } = await api.DELETE("/api/v1/applications/{application_id}", {
        params: { path: { application_id: application.id } },
      });
      if (error) throw error;
    },
    onSuccess: onDeleted,
  });

  return (
    <Dialog open onClose={onClose} fullWidth>
      <DialogTitle>Delete “{application.role}”?</DialogTitle>
      <DialogContent>
        {remove.error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Could not delete the application
          </Alert>
        )}
        <DialogContentText>Its history will be deleted too.</DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          color="error"
          loading={remove.isPending}
          onClick={() => remove.mutate()}
        >
          Delete
        </Button>
      </DialogActions>
    </Dialog>
  );
}
