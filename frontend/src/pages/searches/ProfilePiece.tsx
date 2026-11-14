import { Box, Button, Stack, Typography } from "@mui/material";
import { type ReactNode, useId, useState } from "react";
import { GeneratedSearches } from "./GeneratedSearches";
import { Tokens } from "./Tokens";
import type { Profile } from "./types";

type Props = {
  profile: Profile;
  open: boolean;
  onEdit: () => void;
  onDelete: () => void;
};

// One profile and its two jobs: which offers fit, and the searches it writes.
export function ProfilePiece({ profile, open: startOpen, onEdit, onDelete }: Props) {
  const [open, setOpen] = useState(startOpen);
  const nameId = useId();
  return (
    <Box
      component="section"
      aria-labelledby={nameId}
      sx={{ p: 3, bgcolor: "background.paper", border: 1, borderColor: "divider" }}
    >
      <Box sx={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: 1 }}>
        <Typography id={nameId} variant="h6" component="h2" sx={{ flexGrow: 1 }}>
          {profile.name}
        </Typography>
        <Button
          size="small"
          variant="outlined"
          aria-label={`Edit “${profile.name}”`}
          onClick={onEdit}
        >
          Edit
        </Button>
        <Button
          size="small"
          variant="outlined"
          aria-label={`Delete “${profile.name}”`}
          onClick={onDelete}
        >
          Delete
        </Button>
      </Box>

      {open && (
        <Stack spacing={3} sx={{ mt: 2.5 }}>
          <Box sx={{ display: "grid", gap: 3, gridTemplateColumns: { md: "1fr 1fr" } }}>
            <Column title="Fit by words">
              <Rule label="One of these job titles">
                <Tokens items={profile.titles} kind="title" />
              </Rule>
              <Rule label="All of these keywords">
                <Tokens items={profile.keywords} kind="keyword" />
              </Rule>
              <Rule label="None of these">
                <Tokens items={profile.excluded_keywords} kind="excluded" />
              </Rule>
            </Column>
            <Column title="Fit by the description">
              <Rule label="Doable while living in">
                <Typography variant="body2">{profile.location || "—"}</Typography>
              </Rule>
              <Rule label="Work modes">
                <Tokens items={profile.work_modes} kind="title" />
              </Rule>
              <Typography variant="body2" sx={{ color: "text.secondary" }}>
                Offers that fail any of this go to Inbox › Filtered, never lost. Editing the profile
                recalculates them.
              </Typography>
            </Column>
          </Box>
          <GeneratedSearches profileId={profile.id} />
        </Stack>
      )}

      <Button size="small" onClick={() => setOpen(!open)} sx={{ mt: 2, ml: -1 }}>
        {open ? "Hide fit and searches" : "Show fit and searches"}
      </Button>
    </Box>
  );
}

function Column({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Stack spacing={2}>
      <Typography variant="subtitle1" component="h3" sx={{ fontWeight: 600 }}>
        {title}
      </Typography>
      {children}
    </Stack>
  );
}

function Rule({ label, children }: { label: string; children: ReactNode }) {
  const labelId = useId();
  return (
    <Box role="group" aria-labelledby={labelId}>
      <Typography id={labelId} variant="body2" sx={{ color: "text.secondary", mb: 0.75 }}>
        {label}
      </Typography>
      {children}
    </Box>
  );
}
