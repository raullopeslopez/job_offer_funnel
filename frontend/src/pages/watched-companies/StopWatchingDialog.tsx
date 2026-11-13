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
import type { WatchedCompany } from "../sources/types";

type Props = { company: WatchedCompany | null; onClose: () => void; onStopped: () => void };

export function StopWatchingDialog({ company, onClose, onStopped }: Props) {
  const stop = useMutation({
    mutationFn: async (companyId: string) => {
      const { error } = await api.DELETE("/api/v1/watched-companies/{watched_company_id}", {
        params: { path: { watched_company_id: companyId } },
      });
      if (error) throw error;
    },
    onSuccess: onStopped,
  });

  const close = () => {
    stop.reset();
    onClose();
  };

  return (
    <Dialog open={company !== null} onClose={close} fullWidth>
      <DialogTitle>Stop watching “{company?.name}”?</DialogTitle>
      <DialogContent>
        {stop.error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Could not stop watching the company
          </Alert>
        )}
        <DialogContentText>Its offers already in the inbox are kept.</DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={close}>Cancel</Button>
        <Button
          variant="contained"
          color="error"
          loading={stop.isPending}
          onClick={() => company && stop.mutate(company.id)}
        >
          Stop watching
        </Button>
      </DialogActions>
    </Dialog>
  );
}
