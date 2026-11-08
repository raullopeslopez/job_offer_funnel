import {
  Alert,
  Box,
  Button,
  Link,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type ReactNode, useState } from "react";
import { Link as RouterLink, useNavigate, useParams } from "react-router";
import { api } from "../../api/client";
import type { components } from "../../api/schema";
import { ApplicationDialog } from "./ApplicationDialog";
import { DeleteApplicationDialog } from "./DeleteApplicationDialog";
import { formatDate } from "./options";
import { TransitionDialog } from "./TransitionDialog";
import { UndoTransitionDialog } from "./UndoTransitionDialog";

type Detail = components["schemas"]["ApplicationDetailRead"];

export function ApplicationDetailPage() {
  const { applicationId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [dialog, setDialog] = useState<"edit" | "delete" | "move" | "close" | "undo" | null>(null);
  const refresh = async () => {
    setDialog(null);
    await queryClient.invalidateQueries({ queryKey: ["applications"] });
  };

  const detail = useQuery({
    queryKey: ["applications", applicationId],
    queryFn: async (): Promise<Detail | null> => {
      const { data, error, response } = await api.GET("/api/v1/applications/{application_id}", {
        params: { path: { application_id: applicationId } },
      });
      if (response.status === 404) return null;
      if (error) throw error;
      return data;
    },
  });

  const backLink = (
    <Link component={RouterLink} to="/applications">
      Back to applications
    </Link>
  );

  if (detail.isPending) return null;
  if (!detail.data) {
    return (
      <Stack spacing={2} sx={{ alignItems: "flex-start" }}>
        <Alert severity="error">The application does not exist</Alert>
        {backLink}
      </Stack>
    );
  }

  const application = detail.data;
  return (
    <>
      {backLink}
      <Stack direction="row" spacing={1} sx={{ alignItems: "center", mt: 1 }}>
        <Typography variant="h4" component="h1" sx={{ flexGrow: 1 }}>
          {application.role}
        </Typography>
        <Button variant="outlined" onClick={() => setDialog("edit")}>
          Edit
        </Button>
        <Button color="error" onClick={() => setDialog("delete")}>
          Delete
        </Button>
      </Stack>
      <Typography variant="h6" component="p">
        at {application.company_name}
      </Typography>
      <Stack direction="row" spacing={1} sx={{ alignItems: "center", mb: 3 }}>
        <Typography color="text.secondary" sx={{ flexGrow: 1 }}>
          {application.outcome
            ? `Closed as ${application.outcome} in stage ${application.stage}`
            : `In stage ${application.stage}`}
        </Typography>
        <Button variant="contained" onClick={() => setDialog("move")}>
          Move
        </Button>
        <Button variant="outlined" onClick={() => setDialog("close")}>
          Close
        </Button>
        <Button onClick={() => setDialog("undo")}>Undo last transition</Button>
      </Stack>

      <Box
        component="dl"
        sx={{ display: "grid", gridTemplateColumns: "max-content 1fr", gap: 1, columnGap: 3 }}
      >
        <Field label="Channel">{application.channel}</Field>
        <Field label="Priority">{application.priority}</Field>
        <Field label="URL">
          {application.url && (
            <Link href={application.url} target="_blank" rel="noopener noreferrer">
              {application.url}
            </Link>
          )}
        </Field>
        <Field label="Notes">{application.notes}</Field>
        <Field label="Added">{formatDate(application.created_at)}</Field>
      </Box>

      <Typography variant="h5" component="h2" sx={{ mt: 3, mb: 1 }}>
        History
      </Typography>
      <Table size="small" aria-label="History">
        <TableHead>
          <TableRow>
            <TableCell>Stage</TableCell>
            <TableCell>Outcome</TableCell>
            <TableCell>Date</TableCell>
            <TableCell>Note</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {application.transitions.map((transition) => (
            <TableRow
              key={`${transition.to_stage}-${transition.outcome}-${transition.occurred_on}`}
            >
              <TableCell>{transition.to_stage}</TableCell>
              <TableCell>{transition.outcome}</TableCell>
              <TableCell>{formatDate(transition.occurred_on)}</TableCell>
              <TableCell>{transition.note}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {dialog === "edit" && (
        <ApplicationDialog
          application={application}
          onClose={() => setDialog(null)}
          onSaved={refresh}
        />
      )}
      {(dialog === "move" || dialog === "close") && (
        <TransitionDialog
          application={application}
          mode={dialog}
          onClose={() => setDialog(null)}
          onSaved={refresh}
        />
      )}
      {dialog === "undo" && (
        <UndoTransitionDialog
          application={application}
          onClose={() => setDialog(null)}
          onUndone={refresh}
        />
      )}
      {dialog === "delete" && (
        <DeleteApplicationDialog
          application={application}
          onClose={() => setDialog(null)}
          onDeleted={async () => {
            await navigate("/applications");
            queryClient.removeQueries({ queryKey: ["applications", applicationId] });
            await queryClient.invalidateQueries({ queryKey: ["applications"] });
          }}
        />
      )}
    </>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <Typography component="dt" color="text.secondary">
        {label}
      </Typography>
      <Typography component="dd" sx={{ m: 0 }}>
        {children || "—"}
      </Typography>
    </>
  );
}
