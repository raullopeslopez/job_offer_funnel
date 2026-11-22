import { Button, Stack, Typography } from "@mui/material";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";

// "Let AI discard {n}" (specs/ui/inbox.feature): the triager discards the pending offers it
// marked KO with high confidence (specs/inbox/triager_discards.feature), always by my
// click. It only shows while there is something to discard.
export function TriagerDiscardButton({ onDiscarded }: { onDiscarded: (ids: string[]) => void }) {
  const triager = useQuery({
    queryKey: ["offers", "triager"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/offers/triager");
      if (error) throw error;
      return data;
    },
  });

  const discard = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST("/api/v1/offers/triager-discards");
      if (error) throw error;
      return data.offer_ids;
    },
    onSuccess: onDiscarded,
  });

  const count = triager.data?.discardable ?? 0;
  if (count === 0) return null;
  return (
    <Stack
      direction="row"
      spacing={1.5}
      useFlexGap
      sx={{ alignItems: "baseline", flexWrap: "wrap" }}
    >
      <Button size="small" loading={discard.isPending} onClick={() => discard.mutate()}>
        Let AI discard {count}
      </Button>
      <Typography variant="body2" color="text.secondary">
        The ones it marked KO with high confidence. You can restore any of them.
      </Typography>
      {discard.isError && (
        <Typography variant="body2" color="error" role="alert">
          The AI could not discard.
        </Typography>
      )}
    </Stack>
  );
}
