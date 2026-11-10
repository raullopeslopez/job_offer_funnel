import { Box, Button, Snackbar, Stack, Tab, Tabs, Typography } from "@mui/material";
import type { GridPaginationModel } from "@mui/x-data-grid";
import {
  keepPreviousData,
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useState } from "react";
import { useSearchParams } from "react-router";
import { api } from "../../api/client";
import { TabLabel } from "../../components/TabLabel";
import { AddOfferDialog } from "./AddOfferDialog";
import { DiscardDialog } from "./DiscardDialog";
import { ImportJobBoardDialog } from "./ImportJobBoardDialog";
import { type Offer, type OfferStatus, OffersGrid, type OfferView } from "./OffersGrid";
import { PromoteDialog } from "./PromoteDialog";

// The pending offers are split: those that fit a search profile and the filtered ones
// (specs/inbox/filtered_offers.feature).
type View = OfferView;
const VIEWS: { value: View; label: string }[] = [
  { value: "pending", label: "Pending" },
  { value: "filtered", label: "Filtered" },
  { value: "discarded", label: "Discarded" },
  { value: "promoted", label: "Promoted" },
];

function viewQuery(view: View): { status: OfferStatus; filtered?: boolean } {
  if (view === "filtered") return { status: "pending", filtered: true };
  return view === "pending" ? { status: view, filtered: false } : { status: view };
}
const PAGE_SIZE = 20;

type Notice = { message: string; undoDiscardOf?: string };

export function InboxPage() {
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const view = (params.get("status") as View | null) ?? "pending";
  const [pagination, setPagination] = useState<GridPaginationModel>({
    page: 0,
    pageSize: PAGE_SIZE,
  });
  const [dialog, setDialog] = useState<"add" | "import" | null>(null);
  const [discarding, setDiscarding] = useState<Offer | null>(null);
  const [promoting, setPromoting] = useState<Offer | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);

  const offers = useQuery({
    queryKey: ["offers", view, pagination.page, pagination.pageSize],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/offers", {
        params: {
          query: {
            ...viewQuery(view),
            limit: pagination.pageSize,
            offset: pagination.page * pagination.pageSize,
          },
        },
      });
      if (error) throw error;
      return data;
    },
    placeholderData: keepPreviousData,
  });

  const counts = useQueries({
    queries: VIEWS.map(({ value }) => ({
      queryKey: ["offers", "count", value],
      queryFn: async () => {
        const { data, error } = await api.GET("/api/v1/offers", {
          params: { query: { ...viewQuery(value), limit: 1 } },
        });
        if (error) throw error;
        return data.total;
      },
    })),
  });

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["offers"] });

  const restore = useMutation({
    mutationFn: async (offerId: string) => {
      const { error } = await api.DELETE("/api/v1/offers/{offer_id}/discard", {
        params: { path: { offer_id: offerId } },
      });
      if (error) throw error;
    },
    onSuccess: async () => {
      await refresh();
      setNotice({ message: "Offer restored" });
    },
  });

  const changeView = (next: View) => {
    setParams(next === "pending" ? {} : { status: next });
    setPagination((current) => ({ ...current, page: 0 }));
  };

  const total = offers.data?.total ?? 0;

  return (
    <>
      <Stack direction="row" sx={{ alignItems: "center", mb: 2 }} spacing={2}>
        <Typography variant="h4" component="h1" sx={{ flexGrow: 1 }}>
          Inbox
        </Typography>
        <Button variant="outlined" onClick={() => setDialog("import")}>
          Import job board
        </Button>
        <Button variant="contained" onClick={() => setDialog("add")}>
          Add offer
        </Button>
      </Stack>

      <Tabs value={view} onChange={(_, next: View) => changeView(next)} sx={{ mb: 2 }}>
        {VIEWS.map(({ value, label }, index) => (
          <Tab
            key={value}
            value={value}
            label={<TabLabel label={label} count={counts[index]?.data ?? 0} />}
          />
        ))}
      </Tabs>

      <Typography color="text.secondary" sx={{ mb: 1 }}>
        {total === 1 ? "1 offer" : `${total} offers`}
      </Typography>

      <Box>
        <OffersGrid
          status={view}
          offers={offers.data?.items ?? []}
          total={total}
          loading={offers.isFetching}
          pagination={pagination}
          onPaginationChange={setPagination}
          onDiscard={setDiscarding}
          onPromote={setPromoting}
          onRestore={(offer) => restore.mutate(offer.id)}
        />
      </Box>

      <AddOfferDialog
        open={dialog === "add"}
        onClose={() => setDialog(null)}
        onAdded={async () => {
          setDialog(null);
          changeView("pending");
          await refresh();
        }}
      />
      <ImportJobBoardDialog open={dialog === "import"} onClose={() => setDialog(null)} />
      <DiscardDialog
        offer={discarding}
        onClose={() => setDiscarding(null)}
        onDiscarded={async (offer) => {
          setDiscarding(null);
          await refresh();
          setNotice({ message: "Offer discarded", undoDiscardOf: offer.id });
        }}
      />
      <PromoteDialog
        offer={promoting}
        onClose={() => setPromoting(null)}
        onPromoted={async () => {
          setPromoting(null);
          await refresh();
          setNotice({ message: "Application created" });
        }}
      />

      <Snackbar
        open={notice !== null}
        autoHideDuration={6000}
        onClose={() => setNotice(null)}
        message={notice?.message}
        action={
          notice?.undoDiscardOf && (
            <Button
              color="inherit"
              size="small"
              onClick={() => {
                const offerId = notice.undoDiscardOf;
                setNotice(null);
                if (offerId) restore.mutate(offerId);
              }}
            >
              Undo
            </Button>
          )
        }
      />
    </>
  );
}
