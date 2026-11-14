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
import type { Profile } from "./types";

type Props = { profile: Profile | null; onClose: () => void; onDeleted: () => void };

export function DeleteProfileDialog({ profile, onClose, onDeleted }: Props) {
  const remove = useMutation({
    mutationFn: async (profileId: string) => {
      const { error } = await api.DELETE("/api/v1/search-profiles/{profile_id}", {
        params: { path: { profile_id: profileId } },
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
    <Dialog open={profile !== null} onClose={close} fullWidth>
      <DialogTitle>Delete “{profile?.name}”?</DialogTitle>
      <DialogContent>
        {remove.error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Could not delete the profile
          </Alert>
        )}
        <DialogContentText>Its searches will no longer be shown.</DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={close}>Cancel</Button>
        <Button
          variant="contained"
          color="error"
          loading={remove.isPending}
          onClick={() => profile && remove.mutate(profile.id)}
        >
          Delete
        </Button>
      </DialogActions>
    </Dialog>
  );
}
