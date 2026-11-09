import type { SvgIconComponent } from "@mui/icons-material";
import AltRouteOutlined from "@mui/icons-material/AltRouteOutlined";
import EventOutlined from "@mui/icons-material/EventOutlined";
import FlagOutlined from "@mui/icons-material/FlagOutlined";
import LinkOutlined from "@mui/icons-material/LinkOutlined";
import NotesOutlined from "@mui/icons-material/NotesOutlined";
import { Alert, Box, Button, Link, Paper, Stack, Typography } from "@mui/material";
import { alpha } from "@mui/material/styles";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type ReactNode, useState } from "react";
import { Link as RouterLink, useNavigate, useParams } from "react-router";
import { api } from "../../api/client";
import type { components } from "../../api/schema";
import { CompanyAvatar } from "../../components/CompanyAvatar";
import { channelIcons, outcomeIcons, stageIcons } from "../../components/icons";
import { PriorityBars } from "../../components/PriorityBars";
import { StageProgress } from "../../components/StageProgress";
import { StatusChip } from "../../components/StatusChip";
import { mono } from "../../theme";
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
      <Stack direction="row" spacing={1.25} sx={{ alignItems: "center", mb: 3 }}>
        <CompanyAvatar name={application.company_name} size={28} />
        <Typography variant="h6" component="p" color="text.secondary" sx={{ fontWeight: 400 }}>
          at {application.company_name}
        </Typography>
      </Stack>
      <Paper sx={{ p: { xs: 2, md: 2.5 }, mb: 3.5 }}>
        <Stack direction="row" sx={{ alignItems: "center", gap: 2, flexWrap: "wrap" }}>
          <Stack spacing={1.25} sx={{ flex: "1 1 260px" }}>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
                flexWrap: "wrap",
                color: "text.secondary",
              }}
            >
              {application.outcome ? (
                <>
                  Closed as <StatusChip value={application.outcome} /> in stage{" "}
                  <StatusChip value={application.stage} />
                </>
              ) : (
                <>
                  In stage <StatusChip value={application.stage} size="medium" />
                </>
              )}
            </Box>
            <StageProgress stage={application.stage} outcome={application.outcome} size="large" />
          </Stack>
          <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexWrap: "wrap" }}>
            <Button variant="contained" onClick={() => setDialog("move")}>
              Move
            </Button>
            <Button variant="outlined" onClick={() => setDialog("close")}>
              Close
            </Button>
            <Button onClick={() => setDialog("undo")}>Undo last transition</Button>
          </Stack>
        </Stack>
      </Paper>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "minmax(0, 1fr)", md: "minmax(280px, 1fr) minmax(0, 1.6fr)" },
          gap: 3.5,
          alignItems: "start",
        }}
      >
        <Box component="section" sx={{ minWidth: 0 }}>
          <Typography variant="h5" component="h2" sx={{ mb: 1 }}>
            Details
          </Typography>
          <Paper sx={{ p: { xs: 2, md: 2.5 } }}>
            <Box
              component="dl"
              sx={{
                display: "grid",
                gridTemplateColumns: "max-content 1fr",
                rowGap: 1.5,
                columnGap: 3,
                m: 0,
                alignItems: "center",
              }}
            >
              <Field label="Channel" icon={AltRouteOutlined}>
                {application.channel && <ChannelValue channel={application.channel} />}
              </Field>
              <Field label="Priority" icon={FlagOutlined}>
                {application.priority && <PriorityBars value={application.priority} />}
              </Field>
              <Field label="URL" icon={LinkOutlined}>
                {application.url && (
                  <Link href={application.url} target="_blank" rel="noopener noreferrer">
                    {application.url}
                  </Link>
                )}
              </Field>
              <Field label="Notes" icon={NotesOutlined}>
                {application.notes}
              </Field>
              <Field label="Added" icon={EventOutlined}>
                {formatDate(application.created_at)}
              </Field>
            </Box>
          </Paper>
        </Box>

        <Box component="section" sx={{ minWidth: 0 }}>
          <Typography variant="h5" component="h2" sx={{ mb: 1 }}>
            History
          </Typography>
          <Paper sx={{ p: { xs: 2, md: 2.5 } }}>
            <Timeline transitions={application.transitions} />
          </Paper>
        </Box>
      </Box>

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

function Field({
  label,
  icon: Icon,
  children,
}: {
  label: string;
  icon: SvgIconComponent;
  children: ReactNode;
}) {
  return (
    <>
      <Typography
        component="dt"
        color="text.secondary"
        sx={{ display: "flex", alignItems: "center", gap: 1 }}
      >
        <Icon aria-hidden sx={{ fontSize: 18, color: "text.secondary" }} />
        {label}
      </Typography>
      <Typography component="dd" sx={{ m: 0, minWidth: 0, overflowWrap: "anywhere" }}>
        {children || "—"}
      </Typography>
    </>
  );
}

function ChannelValue({ channel }: { channel: string }) {
  const Icon = channelIcons[channel];
  return (
    <Box component="span" sx={{ display: "inline-flex", alignItems: "center", gap: 0.5 }}>
      {Icon && <Icon aria-hidden sx={{ fontSize: 14 }} />}
      {channel}
    </Box>
  );
}

// Vertical timeline, newest first; the first dot is highlighted as the current state.
function Timeline({ transitions }: { transitions: Detail["transitions"] }) {
  const items = [...transitions].reverse();
  return (
    <Box component="ol" aria-label="History" sx={{ listStyle: "none", m: 0, p: 0 }}>
      {items.map((transition, i) => {
        const last = i === items.length - 1;
        const Icon = outcomeIcons[transition.outcome ?? ""] ?? stageIcons[transition.to_stage];
        return (
          <Box
            component="li"
            key={`${transition.to_stage}-${transition.outcome}-${transition.occurred_on}`}
            sx={{ display: "grid", gridTemplateColumns: "28px 1fr", columnGap: 1.75 }}
          >
            <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
              <Box
                aria-hidden
                sx={(theme) => ({
                  width: 28,
                  height: 28,
                  borderRadius: "50%",
                  display: "grid",
                  placeItems: "center",
                  bgcolor:
                    i === 0
                      ? theme.vars
                        ? `rgba(${theme.vars.palette.primary.mainChannel} / 0.12)`
                        : alpha(theme.palette.primary.main, 0.12)
                      : (theme.vars ?? theme).palette.tone.neutral.bg,
                  color: i === 0 ? "primary.main" : "text.secondary",
                })}
              >
                {Icon && <Icon sx={{ fontSize: 15 }} />}
              </Box>
              {!last && (
                <Box sx={{ flex: 1, width: "1px", minHeight: 16, my: 0.5, bgcolor: "divider" }} />
              )}
            </Box>
            <Box sx={{ pb: last ? 0 : 2.5, minWidth: 0 }}>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 1,
                  flexWrap: "wrap",
                  minHeight: 28,
                }}
              >
                <StatusChip value={transition.to_stage} icon={false} />
                {transition.outcome && <StatusChip value={transition.outcome} icon={false} />}
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ ml: "auto", fontFamily: mono }}
                >
                  {formatDate(transition.occurred_on)}
                </Typography>
              </Box>
              {transition.note && (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75 }}>
                  {transition.note}
                </Typography>
              )}
            </Box>
          </Box>
        );
      })}
    </Box>
  );
}
