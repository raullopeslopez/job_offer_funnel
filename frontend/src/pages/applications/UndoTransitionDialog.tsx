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
import type { components } from "../../api/schema";
import type { Application } from "./options";

type Problem = components["schemas"]["ProblemRead"];
type Props = { application: Application; onClose: () => void; onUndone: () => void };

export function UndoTransitionDialog({ application, onClose, onUndone }: Props) {
  const undo = useMutation<void, Problem>({
    mutationFn: async () => {
      const { error } = await api.DELETE(
        "/api/v1/applications/{application_id}/transitions/latest",
        { params: { path: { application_id: application.id } } },
      );
      if (error) throw error;
    },
    onSuccess: onUndone,
  });

  return (
    <Dialog open onClose={onClose} fullWidth>
      <DialogTitle>Undo the last transition of “{application.role}”?</DialogTitle>
      <DialogContent>
        {undo.error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {undo.error.detail ?? undo.error.title}
          </Alert>
        )}
        <DialogContentText>
          The application returns to where it was before it, and the transition leaves the history.
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" loading={undo.isPending} onClick={() => undo.mutate()}>
          Undo
        </Button>
      </DialogActions>
    </Dialog>
  );
}
