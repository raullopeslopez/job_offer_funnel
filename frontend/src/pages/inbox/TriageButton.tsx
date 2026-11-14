import { Button, Stack, Typography } from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../api/client";

type Progress = { triaged: number; left: number; isStopped: boolean };

// "Triage with AI" (specs/ui/inbox.feature): batch after batch until none is left, and it
// stops when a batch triages none (the triager's limits, or it failed on all of them).
// Without an offer triager it does not show.
export function TriageButton() {
  const queryClient = useQueryClient();
  const [progress, setProgress] = useState<Progress | null>(null);

  const triager = useQuery({
    queryKey: ["offers", "triager"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/offers/triager");
      if (error) throw error;
      return data;
    },
  });

  const triage = useMutation({
    mutationFn: async () => {
      let triaged = 0;
      for (;;) {
        const { data, error } = await api.POST("/api/v1/offers/triages");
        if (error) throw error;
        triaged += data.triaged;
        const isStopped = data.triaged === 0 && data.left > 0;
        setProgress({ triaged, left: data.left, isStopped });
        await queryClient.invalidateQueries({ queryKey: ["offers"], exact: false });
        if (data.left === 0 || isStopped) return;
      }
    },
  });

  if (!triager.data?.is_available) return null;
  return (
    <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
      {triage.isError && (
        <Typography variant="body2" color="error" role="alert">
          The triage failed.
        </Typography>
      )}
      {progress && (
        <Typography variant="body2" color="text.secondary" role="status">
          Triaged {progress.triaged} · {progress.left} left
          {progress.isStopped ? ". Try again later." : ""}
        </Typography>
      )}
      <Button variant="outlined" loading={triage.isPending} onClick={() => triage.mutate()}>
        Triage with AI
      </Button>
    </Stack>
  );
}
