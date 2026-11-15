import { Box, Button, Snackbar, Stack, Typography } from "@mui/material";
import {
  useInfiniteQuery,
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useState } from "react";
import { useSearchParams } from "react-router";
import { api } from "../../api/client";
import { SegmentedTabs } from "../../components/SegmentedTabs";
import { AddOfferDialog } from "./AddOfferDialog";
import { FrequentTitles } from "./FrequentTitles";
import { ImportJobBoardDialog } from "./ImportJobBoardDialog";
import { MaybeGroup } from "./MaybeGroup";
import { NearMissGroups } from "./NearMissGroups";
import { OfferList } from "./OfferList";
import { PromoteDialog } from "./PromoteDialog";
import { TriageButton } from "./TriageButton";
import { TriagerSuggestion } from "./TriagerSuggestion";
import type { Offer, OfferStatus, OfferView } from "./types";

// The pending offers are split: those that fit a search profile and the filtered ones
// (specs/inbox/filtered_offers.feature).
type View = OfferView;
const VIEWS: { value: View; label: string; heading: string }[] = [
  { value: "pending", label: "Pending", heading: "to decide" },
  { value: "filtered", label: "Filtered", heading: "filtered" },
  { value: "discarded", label: "Discarded", heading: "discarded" },
  { value: "promoted", label: "Promoted", heading: "promoted" },
];

function viewQuery(view: View): { status: OfferStatus; filtered?: boolean } {
  if (view === "filtered") return { status: "pending", filtered: true };
  return view === "pending" ? { status: view, filtered: false } : { status: view };
}
// The filtered view lists the near misses by rule, and then the rest: those further away.
// The pending view goes by the triager's verdict (specs/inbox/offer_triages.feature), with the
// variants of each offer together (specs/inbox/offer_variants.feature).
function listQuery(view: View) {
  if (view === "filtered") return { ...viewQuery(view), near_miss: false };
  return view === "pending"
    ? { ...viewQuery(view), by_verdict: true, variants_together: true }
    : viewQuery(view);
}
// The count of a view: the tabs show it, and the navigation the one of the pending offers.
export function offerCountQuery(view: View) {
  return {
    queryKey: ["offers", "count", view],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/offers", {
        params: { query: { ...viewQuery(view), limit: 1 } },
      });
      if (error) throw error;
      return data.total;
    },
  };
}

const PAGE_SIZE = 20;

type Notice = { message: string; undo?: () => void };

export function InboxPage() {
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const view = (params.get("status") as View | null) ?? "pending";
  const [dialog, setDialog] = useState<"add" | "import" | null>(null);
  const [discarding, setDiscarding] = useState<Offer | null>(null);
  const [promoting, setPromoting] = useState<Offer | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);

  const offers = useInfiniteQuery({
    queryKey: ["offers", view],
    initialPageParam: 0,
    queryFn: async ({ pageParam }) => {
      const { data, error } = await api.GET("/api/v1/offers", {
        params: { query: { ...listQuery(view), limit: PAGE_SIZE, offset: pageParam } },
      });
      if (error) throw error;
      return data;
    },
    getNextPageParam: (last) =>
      last.offset + last.items.length < last.total ? last.offset + last.items.length : undefined,
  });

  // The import method of each job board tells the source of its offers.
  const jobBoards = useQuery({
    queryKey: ["job-boards"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/job-boards", {
        params: { query: { limit: 100 } },
      });
      if (error) throw error;
      return data.items;
    },
  });

  // The profiles say what each rule asks, for the cells of the strip.
  const profiles = useQuery({
    queryKey: ["search-profiles", "all"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/search-profiles", {
        params: { query: { limit: 100 } },
      });
      if (error) throw error;
      return data.items;
    },
  });

  const counts = useQueries({
    queries: VIEWS.map(({ value }) => offerCountQuery(value)),
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

  // A near miss left filtered (specs/inbox/rescues.feature); undone from the notice.
  const unmark = useMutation({
    mutationFn: async (offerId: string) => {
      const { error } = await api.DELETE("/api/v1/offers/{offer_id}/rightly-filtered", {
        params: { path: { offer_id: offerId } },
      });
      if (error) throw error;
    },
    onSuccess: refresh,
  });
  const markRightlyFiltered = useMutation({
    mutationFn: async (offer: Offer) => {
      const { error } = await api.POST("/api/v1/offers/{offer_id}/rightly-filtered", {
        params: { path: { offer_id: offer.id } },
      });
      if (error) throw error;
      return offer;
    },
    onSuccess: async (offer) => {
      await refresh();
      setNotice({ message: "Marked as rightly filtered", undo: () => unmark.mutate(offer.id) });
    },
  });
  const nearMissActions = {
    onPromote: setPromoting,
    onRightlyFiltered: (offer: Offer) => markRightlyFiltered.mutate(offer),
  };

  const changeView = (next: View) => setParams(next === "pending" ? {} : { status: next });

  const pages = offers.data?.pages ?? [];
  const items = pages.flatMap((page) => page.items);
  const listed = pages[0]?.total ?? 0;
  const viewIndex = VIEWS.findIndex(({ value }) => value === view);
  const total = counts[viewIndex]?.data ?? 0;
  const heading = VIEWS[viewIndex]?.heading;
  const context = { jobBoards: jobBoards.data ?? [], profiles: profiles.data ?? [] };

  return (
    <>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        sx={{ alignItems: { sm: "flex-end" }, mb: 3 }}
        spacing={2}
      >
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h4" component="h1">
            {total} {heading}
          </Typography>
          {view === "pending" && (
            <Typography color="text.secondary" sx={{ mt: 1 }}>
              Each offer shows the rules of your profile it passed. Promote it, or discard it and
              say why.
            </Typography>
          )}
        </Box>
        <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
          {view === "pending" && <TriageButton />}
          <Button variant="outlined" onClick={() => setDialog("import")}>
            Import job board
          </Button>
          <Button variant="contained" onClick={() => setDialog("add")}>
            Add offer
          </Button>
        </Stack>
      </Stack>

      <Box sx={{ mb: 3 }}>
        <SegmentedTabs
          aria-label="Offers"
          value={view}
          onChange={changeView}
          items={VIEWS.map(({ value, label }, index) => ({
            value,
            label,
            count: counts[index]?.data ?? 0,
          }))}
        />
      </Box>

      {view === "pending" && <TriagerSuggestion />}
      {view === "filtered" && <NearMissGroups {...context} {...nearMissActions} />}
      {view === "filtered" && <FrequentTitles profiles={context.profiles} />}

      {offers.isSuccess && (view !== "filtered" || listed > 0 || total === 0) && (
        <OfferList
          view={view}
          offers={items}
          {...context}
          single={view === "filtered" ? { title: "Further away", count: listed } : undefined}
          byVerdict={view === "pending"}
          variants={view === "pending"}
          onDiscard={setDiscarding}
          discardingId={discarding?.id}
          onCancelDiscard={() => setDiscarding(null)}
          onDiscarded={async (offer) => {
            setDiscarding(null);
            await refresh();
            setNotice({ message: "Offer discarded", undo: () => restore.mutate(offer.id) });
          }}
          onPromote={setPromoting}
          onRestore={(offer) => restore.mutate(offer.id)}
        />
      )}

      {offers.hasNextPage && (
        <Box sx={{ display: "flex", justifyContent: "center", mt: 3 }}>
          <Button
            variant="outlined"
            loading={offers.isFetchingNextPage}
            onClick={() => offers.fetchNextPage()}
          >
            Show more
          </Button>
        </Box>
      )}

      {view === "pending" && <MaybeGroup {...context} {...nearMissActions} />}

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
          notice?.undo && (
            <Button
              color="inherit"
              size="small"
              onClick={() => {
                notice.undo?.();
                setNotice(null);
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
