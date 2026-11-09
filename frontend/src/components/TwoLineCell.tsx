import type { SvgIconComponent } from "@mui/icons-material";
import { Box } from "@mui/material";
import type { ReactNode } from "react";
import { mono as monoFont } from "../theme";

const ellipsis = { overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" } as const;

type Props = { lead?: ReactNode; primary: ReactNode; secondary?: ReactNode };

// Row identity: a lead (avatar or tile), a main line and an optional muted line.
export function TwoLineCell({ lead, primary, secondary }: Props) {
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: "12px", minWidth: 0, width: "100%" }}>
      {lead}
      <Box sx={{ minWidth: 0, display: "grid", gap: "2px" }}>
        <Box sx={{ ...ellipsis, fontWeight: 500 }}>{primary}</Box>
        {secondary && (
          <Box
            sx={(theme) => ({
              ...ellipsis,
              display: "flex",
              alignItems: "center",
              gap: "6px",
              ...theme.typography.caption,
              lineHeight: 1.4,
              color: "text.secondary",
            })}
          >
            {secondary}
          </Box>
        )}
      </Box>
    </Box>
  );
}

type MetaProps = { icon?: SvgIconComponent; children: ReactNode; mono?: boolean };

export function Meta({ icon: Icon, children, mono }: MetaProps) {
  return (
    <Box
      component="span"
      sx={{
        display: "inline-flex",
        alignItems: "center",
        gap: "4px",
        minWidth: 0,
        fontFamily: mono ? monoFont : undefined,
      }}
    >
      {Icon && <Icon aria-hidden sx={{ fontSize: 14 }} />}
      {children}
    </Box>
  );
}

export function Sep() {
  return (
    <Box component="span" aria-hidden sx={{ color: "text.disabled" }}>
      ·
    </Box>
  );
}
