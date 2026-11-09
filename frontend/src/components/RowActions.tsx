import type { SvgIconComponent } from "@mui/icons-material";
import { Box, IconButton, Tooltip } from "@mui/material";
import type { ReactNode } from "react";

type RowActionProps = {
  icon: SvgIconComponent;
  label: string;
  onClick: () => void;
};

// Secondary icon action of a row. The primary action stays a visible text button outside RowActions.
export function RowAction({ icon: Icon, label, onClick }: RowActionProps) {
  return (
    <Tooltip title={label}>
      <IconButton size="small" aria-label={label} onClick={onClick}>
        <Icon aria-hidden fontSize="small" />
      </IconButton>
    </Tooltip>
  );
}

export function RowActions({ children }: { children: ReactNode }) {
  return (
    <Box className="row-actions" sx={{ display: "inline-flex", alignItems: "center", gap: 0.5 }}>
      {children}
    </Box>
  );
}

// Pass to the DataGrid `sx`: with a pointer, row actions show on row hover or focus; on touch they are always visible.
export const rowActionsSx = {
  "@media (hover: hover)": {
    "& .row-actions": {
      opacity: 0,
      transition: "opacity 150ms cubic-bezier(.4,0,.2,1)",
    },
    "& .MuiDataGrid-row:hover .row-actions, & .MuiDataGrid-row:focus-within .row-actions": {
      opacity: 1,
    },
  },
  "@media (hover: none)": {
    "& .row-actions": { opacity: 1 },
  },
};
