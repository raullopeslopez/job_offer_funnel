import { Alert, Box, Button, Paper, TextField, Typography } from "@mui/material";
import { useForm } from "react-hook-form";
import { api } from "../api/client";
import { saveToken } from "./token";

type Values = { token: string };

export function TokenForm() {
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ defaultValues: { token: "" } });

  const onSubmit = handleSubmit(async ({ token }) => {
    try {
      const { response } = await api.GET("/api/v1/watched-companies", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.status === 401) {
        setError("token", { message: "Invalid token" });
      } else if (!response.ok) {
        setError("root", { message: "The API returned an unexpected error" });
      } else {
        saveToken(token);
      }
    } catch {
      setError("root", { message: "Could not reach the API" });
    }
  });

  return (
    <Box sx={{ display: "grid", placeItems: "center", minHeight: "100vh" }}>
      <Paper component="form" onSubmit={onSubmit} noValidate sx={{ p: 4, width: 400 }}>
        <Typography variant="h5" component="h1" gutterBottom>
          Job Offer Funnel
        </Typography>
        <Typography color="text.secondary" sx={{ mb: 3 }}>
          Enter the API token (AUTH_TOKEN) to continue.
        </Typography>
        {errors.root && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {errors.root.message}
          </Alert>
        )}
        <TextField
          {...register("token", { required: "Enter the token" })}
          label="Token"
          type="password"
          fullWidth
          autoFocus
          error={Boolean(errors.token)}
          helperText={errors.token?.message}
          sx={{ mb: 3 }}
        />
        <Button type="submit" variant="contained" fullWidth loading={isSubmitting}>
          Continue
        </Button>
      </Paper>
    </Box>
  );
}
