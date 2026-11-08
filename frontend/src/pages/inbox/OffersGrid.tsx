import { Button, Link, Stack } from "@mui/material";
import { DataGrid, type GridColDef, type GridPaginationModel } from "@mui/x-data-grid";
import type { components } from "../../api/schema";

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

const dateFormat = new Intl.DateTimeFormat("en", { dateStyle: "medium" });

export function OffersGrid({ status, offers, total, loading, pagination, ...props }: Props) {
  const columns: GridColDef<Offer>[] = [
    {
      field: "title",
      headerName: "Title",
      flex: 2,
      sortable: false,
      renderCell: ({ row }) => (
        <Link href={row.url} target="_blank" rel="noopener noreferrer">
          {row.title}
        </Link>
      ),
    },
    { field: "company", headerName: "Company", flex: 1, sortable: false },
    {
      field: "source",
      headerName: "Source",
      flex: 1,
      sortable: false,
      valueGetter: (_, row) => row.job_board_name ?? row.feed ?? "",
    },
    ...(status === "discarded"
      ? [{ field: "discard_reason", headerName: "Reason", flex: 1, sortable: false }]
      : []),
    {
      field: "created_at",
      headerName: "Added",
      width: 130,
      sortable: false,
      valueFormatter: (value: string) => dateFormat.format(new Date(value)),
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
    <DataGrid
      rows={offers}
      columns={columns}
      rowCount={total}
      loading={loading}
      paginationMode="server"
      paginationModel={pagination}
      onPaginationModelChange={props.onPaginationChange}
      pageSizeOptions={[pagination.pageSize]}
      disableColumnMenu
      disableRowSelectionOnClick
      autoHeight
      localeText={{ noRowsLabel: "No offers" }}
    />
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
        <Button size="small" color="inherit" onClick={() => onDiscard(offer)}>
          Discard
        </Button>
      </Stack>
    );
  }
  if (offer.status === "discarded") {
    return (
      <Button size="small" onClick={() => onRestore(offer)}>
        Restore
      </Button>
    );
  }
  return null;
}
