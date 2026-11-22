import { Box, Button, CircularProgress, Stack, Typography } from "@mui/material";
import { useEffect, useState } from "react";

// After this long without an answer the API is most likely asleep (specs/ui/waking_up.feature).
export const WAKING_UP_AFTER_MS = 3000;

export function WakingUp({ failed, onRetry }: { failed: boolean; onRetry: () => void }) {
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => setSlow(true), WAKING_UP_AFTER_MS);
    return () => clearTimeout(timer);
  }, []);

  return (
    <Stack spacing={2} sx={{ alignItems: "center", textAlign: "center", pt: { xs: 12, md: 16 } }}>
      {failed ? (
        <>
          <Typography color="text.secondary">The server did not answer.</Typography>
          <Button variant="outlined" onClick={onRetry}>
            Try again
          </Button>
        </>
      ) : (
        <>
          <CircularProgress aria-label="Loading" />
          <Box sx={{ minHeight: 24 }}>
            {slow && (
              <Typography variant="body2" color="text.secondary" role="status">
                Waking up the server. It can take up to a minute.
              </Typography>
            )}
          </Box>
        </>
      )}
    </Stack>
  );
}
