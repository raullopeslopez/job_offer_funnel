import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
} from "@mui/material";
import { useForm } from "react-hook-form";
import { api } from "../../api/client";
import type { Offer } from "./OffersGrid";

type Props = { offer: Offer | null; onClose: () => void; onDiscarded: (offer: Offer) => void };

export function DiscardDialog({ offer, onClose, onDiscarded }: Props) {
  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<{ reason: string }>({ defaultValues: { reason: "" } });

  const close = () => {
    reset();
    onClose();
  };

  const onSubmit = handleSubmit(async ({ reason }) => {
    if (!offer) return;
    const { error } = await api.POST("/api/v1/offers/{offer_id}/discard", {
      params: { path: { offer_id: offer.id } },
      body: { reason: reason || null },
    });
    if (error) {
      setError("root", { message: error.title });
      return;
    }
    reset();
    onDiscarded(offer);
  });

  return (
    <Dialog open={offer !== null} onClose={close} fullWidth>
      <form onSubmit={onSubmit} noValidate>
        <DialogTitle>Discard “{offer?.title}”</DialogTitle>
        <DialogContent>
          {errors.root && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {errors.root.message}
            </Alert>
          )}
          <TextField
            {...register("reason")}
            label="Reason"
            placeholder="Optional"
            fullWidth
            autoFocus
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={close}>Cancel</Button>
          <Button type="submit" variant="contained" loading={isSubmitting}>
            Discard
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
