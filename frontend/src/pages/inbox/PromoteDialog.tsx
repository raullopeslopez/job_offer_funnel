import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  MenuItem,
  TextField,
} from "@mui/material";
import { useRef } from "react";
import { Controller, useForm } from "react-hook-form";
import { api } from "../../api/client";
import { CHANNELS, type Channel } from "../applications/options";
import type { Offer } from "./types";

type Props = { offer: Offer | null; onClose: () => void; onPromoted: () => void };

export function PromoteDialog({ offer, onClose, onPromoted }: Props) {
  const {
    control,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<{ channel: Channel }>({ defaultValues: { channel: "portal" } });

  const promote = useRef<HTMLButtonElement>(null);

  const close = () => {
    reset();
    onClose();
  };

  const onSubmit = handleSubmit(async ({ channel }) => {
    if (!offer) return;
    const { error } = await api.POST("/api/v1/offers/{offer_id}/promotion", {
      params: { path: { offer_id: offer.id } },
      body: { channel },
    });
    if (error) {
      setError("root", { message: error.title });
      return;
    }
    reset();
    onPromoted();
  });

  return (
    <Dialog
      open={offer !== null}
      onClose={close}
      fullWidth
      // So that "P", then Enter promotes: the dialog takes the focus first, so this waits for it.
      slotProps={{ transition: { onEntered: () => promote.current?.focus() } }}
    >
      <form onSubmit={onSubmit} noValidate>
        <DialogTitle>Promote “{offer?.title}”</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            Creates an application in stage evaluated for {offer?.company}.
          </DialogContentText>
          {errors.root && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {errors.root.message}
            </Alert>
          )}
          <Controller
            name="channel"
            control={control}
            render={({ field }) => (
              <TextField {...field} select label="Channel" fullWidth>
                {CHANNELS.map((channel) => (
                  <MenuItem key={channel} value={channel}>
                    {channel}
                  </MenuItem>
                ))}
              </TextField>
            )}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={close}>Cancel</Button>
          <Button type="submit" variant="contained" loading={isSubmitting} ref={promote}>
            Promote
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
