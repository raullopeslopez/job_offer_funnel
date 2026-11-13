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
import type { JobBoard } from "../sources/types";

type Props = { jobBoard: JobBoard | null; onClose: () => void; onDeleted: () => void };

export function DeleteJobBoardDialog({ jobBoard, onClose, onDeleted }: Props) {
  const remove = useMutation({
    mutationFn: async (jobBoardId: string) => {
      const { error } = await api.DELETE("/api/v1/job-boards/{job_board_id}", {
        params: { path: { job_board_id: jobBoardId } },
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
    <Dialog open={jobBoard !== null} onClose={close} fullWidth>
      <DialogTitle>Delete “{jobBoard?.name}”?</DialogTitle>
      <DialogContent>
        {remove.error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Could not delete the job board
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
          onClick={() => jobBoard && remove.mutate(jobBoard.id)}
        >
          Delete
        </Button>
      </DialogActions>
    </Dialog>
  );
}
