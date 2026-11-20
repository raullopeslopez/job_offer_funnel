import ChevronLeft from "@mui/icons-material/ChevronLeft";
import ChevronRight from "@mui/icons-material/ChevronRight";
import { Box, IconButton, LinearProgress, Stack, Typography } from "@mui/material";
import type { GridPaginationModel } from "@mui/x-data-grid";
import type { ReactNode } from "react";
import { offerShape } from "../theme";

type Props<T> = {
  "aria-label": string;
  rows: T[];
  rowKey: (row: T) => string;
  renderCard: (row: T) => ReactNode;
  total: number;
  loading: boolean;
  pagination: GridPaginationModel;
  onPaginationChange: (model: GridPaginationModel) => void;
  empty: ReactNode;
};

// A listing as cards, for a phone: the same rows and pages as its DataGrid on wider screens,
// one card per row with nothing cut, and the pager under them.
export function CardList<T>({
  "aria-label": ariaLabel,
  rows,
  rowKey,
  renderCard,
  total,
  loading,
  pagination,
  onPaginationChange,
  empty,
}: Props<T>) {
  const { page, pageSize } = pagination;
  const first = total === 0 ? 0 : page * pageSize + 1;
  const last = Math.min(total, (page + 1) * pageSize);
  return (
    <Box>
      {loading && <LinearProgress sx={{ mb: 1 }} />}
      {rows.length === 0 && !loading ? (
        empty
      ) : (
        <Stack
          component="ul"
          aria-label={ariaLabel}
          spacing={1}
          sx={{ listStyle: "none", m: 0, p: 0 }}
        >
          {rows.map((row) => (
            <Box
              component="li"
              key={rowKey(row)}
              sx={{
                p: 2,
                bgcolor: "background.paper",
                border: 1,
                borderColor: "divider",
                borderRadius: offerShape.pieceRadius,
              }}
            >
              {renderCard(row)}
            </Box>
          ))}
        </Stack>
      )}
      {total > pageSize && (
        <Stack
          direction="row"
          sx={{ alignItems: "center", justifyContent: "flex-end", gap: 1, mt: 1 }}
        >
          <Typography variant="body2" color="text.secondary">
            {first}–{last} of {total}
          </Typography>
          <IconButton
            aria-label="Go to previous page"
            disabled={page === 0}
            onClick={() => onPaginationChange({ page: page - 1, pageSize })}
          >
            <ChevronLeft />
          </IconButton>
          <IconButton
            aria-label="Go to next page"
            disabled={last >= total}
            onClick={() => onPaginationChange({ page: page + 1, pageSize })}
          >
            <ChevronRight />
          </IconButton>
        </Stack>
      )}
    </Box>
  );
}
