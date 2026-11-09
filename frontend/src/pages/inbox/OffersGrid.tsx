import type { SvgIconComponent } from "@mui/icons-material";
import ArrowUpwardOutlined from "@mui/icons-material/ArrowUpwardOutlined";
import CloseOutlined from "@mui/icons-material/CloseOutlined";
import DeleteOutlineOutlined from "@mui/icons-material/DeleteOutlineOutlined";
import InboxOutlined from "@mui/icons-material/InboxOutlined";
import { Box, Button, Link, Stack } from "@mui/material";
import { DataGrid, type GridColDef, type GridPaginationModel } from "@mui/x-data-grid";
import type { components } from "../../api/schema";
import { CompanyAvatar } from "../../components/CompanyAvatar";
import { EmptyState } from "../../components/EmptyState";
import { offerSourceIcon } from "../../components/icons";
import { RelativeDate } from "../../components/RelativeDate";
import { RowAction, RowActions, rowActionsSx } from "../../components/RowActions";
import { Meta, Sep, TwoLineCell } from "../../components/TwoLineCell";
import { useNarrowGrid } from "../../components/useNarrowGrid";

export type Offer = components["schemas"]["OfferRead"];
export type OfferStatus = components["schemas"]["OfferStatus"];

type Props = {
  status: OfferStatus;
  offers: Offer[];
  total: number;
  loading: boolean;
  pagination: GridPaginationModel;
  onPaginationChange: (model: GridPaginationModel) => void;
  onDiscard: (offer: Offer) => void;
  onPromote: (offer: Offer) => void;
  onRestore: (offer: Offer) => void;
};

const EMPTY: Record<OfferStatus, { icon: SvgIconComponent; text: string }> = {
  pending: { icon: InboxOutlined, text: "Import a feed or add an offer to fill the inbox." },
  discarded: {
    icon: DeleteOutlineOutlined,
    text: "Discarded offers are kept here so you can restore them.",
  },
  promoted: { icon: ArrowUpwardOutlined, text: "Promoted offers become applications." },
};

export function OffersGrid({ status, offers, total, loading, pagination, ...props }: Props) {
  const [containerRef, narrow] = useNarrowGrid();
  const empty = EMPTY[status];

  const columns: GridColDef<Offer>[] = [
    {
      field: "title",
      headerName: "Offer",
      flex: 3,
      minWidth: 220,
      sortable: false,
      renderCell: ({ row }) => {
        const source = row.job_board_name ?? row.watched_company_name ?? row.feed ?? "manual";
        return (
          <TwoLineCell
            lead={<CompanyAvatar name={row.company} />}
            primary={
              <Link href={row.url} target="_blank" rel="noopener noreferrer">
                {row.title}
              </Link>
            }
            secondary={
              <>
                {row.company || "—"}
                <Sep />
                <Meta icon={offerSourceIcon(row)}>{source}</Meta>
              </>
            }
          />
        );
      },
    },
    ...(status === "discarded"
      ? [
          {
            field: "discard_reason",
            headerName: "Reason",
            flex: 1,
            sortable: false,
            valueGetter: (_: unknown, row: Offer) => row.discard_reason || "—",
          },
        ]
      : []),
    {
      field: "created_at",
      headerName: "Added",
      width: 120,
      sortable: false,
      renderCell: ({ row }) => <RelativeDate value={row.created_at} />,
    },
    {
      field: "actions",
      headerName: "",
      width: 200,
      sortable: false,
      renderCell: ({ row }) => <Actions offer={row} {...props} />,
    },
  ];

  return (
    <Box ref={containerRef}>
      <DataGrid
        rows={offers}
        columns={columns}
        columnVisibilityModel={{ discard_reason: !narrow, created_at: !narrow }}
        rowCount={total}
        loading={loading}
        paginationMode="server"
        paginationModel={pagination}
        onPaginationModelChange={props.onPaginationChange}
        pageSizeOptions={[pagination.pageSize]}
        disableColumnMenu
        disableRowSelectionOnClick
        autoHeight
        rowHeight={64}
        sx={rowActionsSx}
        slots={{
          noRowsOverlay: () => <EmptyState icon={empty.icon} title="No offers" text={empty.text} />,
        }}
      />
    </Box>
  );
}

function Actions({
  offer,
  onDiscard,
  onPromote,
  onRestore,
}: { offer: Offer } & Pick<Props, "onDiscard" | "onPromote" | "onRestore">) {
  if (offer.status === "pending") {
    return (
      <Stack direction="row" spacing={1} sx={{ height: "100%", alignItems: "center" }}>
        <Button size="small" onClick={() => onPromote(offer)}>
          Promote
        </Button>
        <RowActions>
          <RowAction
            icon={CloseOutlined}
            label={`Discard “${offer.title}”`}
            onClick={() => onDiscard(offer)}
          />
        </RowActions>
      </Stack>
    );
  }
  if (offer.status === "discarded") {
    return (
      <Stack direction="row" sx={{ height: "100%", alignItems: "center" }}>
        <Button size="small" onClick={() => onRestore(offer)}>
          Restore
        </Button>
      </Stack>
    );
  }
  return null;
}
