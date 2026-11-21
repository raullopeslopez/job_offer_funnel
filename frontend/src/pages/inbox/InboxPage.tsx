import { Box, Button, Snackbar, Stack, Typography } from "@mui/material";
import {
  useInfiniteQuery,
  useIsMutating,
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
import { TriageButton, triageMutationKey } from "./TriageButton";
import { TriagerDiscardButton } from "./TriagerDiscardButton";
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

  // Not awaited: listing the offers again can take long, and what was done shows at once.
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["offers"] });
  };

  // An offer that left the view (discarded, restored, promoted) leaves its list and its
  // count at once, before the inbox lists its offers again.
  const leaveView = (offerId: string) => {
    type Listed = NonNullable<typeof offers.data>;
    const data = queryClient.getQueryData<Listed>(["offers", view]);
    if (!data?.pages.some((page) => page.items.some((o) => o.id === offerId))) return;
    queryClient.setQueryData<Listed>(["offers", view], {
      ...data,
      pages: data.pages.map((page) => ({
        ...page,
        items: page.items.filter((o) => o.id !== offerId),
        total: page.total - 1,
      })),
    });
    queryClient.setQueryData<number>(["offers", "count", view], (count) =>
      count === undefined ? count : Math.max(count - 1, 0),
    );
  };

  const restore = useMutation({
    mutationFn: async (offerId: string) => {
      const { error } = await api.DELETE("/api/v1/offers/{offer_id}/discard", {
        params: { path: { offer_id: offerId } },
      });
      if (error) throw error;
      return offerId;
    },
    onSuccess: (offerId) => {
      leaveView(offerId);
      setNotice({ message: "Offer restored" });
      refresh();
    },
  });

  // Undoing the AI's discards restores each of them (specs/inbox/triager_discards.feature).
  const restoreAll = useMutation({
    mutationFn: async (offerIds: string[]) => {
      for (const offerId of offerIds) {
        const { error } = await api.DELETE("/api/v1/offers/{offer_id}/discard", {
          params: { path: { offer_id: offerId } },
        });
        if (error) throw error;
      }
    },
    onSuccess: () => {
      setNotice({ message: "Offers restored" });
      refresh();
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
    onSuccess: () => refresh(),
  });
  const markRightlyFiltered = useMutation({
    mutationFn: async (offer: Offer) => {
      const { error } = await api.POST("/api/v1/offers/{offer_id}/rightly-filtered", {
        params: { path: { offer_id: offer.id } },
      });
      if (error) throw error;
      return offer;
    },
    onSuccess: (offer) => {
      setNotice({ message: "Marked as rightly filtered", undo: () => unmark.mutate(offer.id) });
      refresh();
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
  const triageRunning = useIsMutating({ mutationKey: triageMutationKey }) > 0;
  const context = { triageRunning, jobBoards: jobBoards.data ?? [], profiles: profiles.data ?? [] };

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
        {/* On a phone the buttons wrap to a new row instead of breaking their labels. */}
        <Stack
          direction="row"
          spacing={1}
          useFlexGap
          sx={{
            alignItems: "center",
            flexWrap: "wrap",
            "& .MuiButton-root": { whiteSpace: "nowrap" },
          }}
        >
          {view === "pending" && (
            <TriagerDiscardButton
              onDiscarded={(offerIds) => {
                for (const offerId of offerIds) leaveView(offerId);
                setNotice({
                  message: `AI discarded ${offerIds.length} offers`,
                  undo: () => restoreAll.mutate(offerIds),
                });
                refresh();
              }}
            />
          )}
          {view === "pending" && <TriageButton running={triageRunning} />}
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
          onDiscarded={(offer) => {
            setDiscarding(null);
            leaveView(offer.id);
            setNotice({ message: "Offer discarded", undo: () => restore.mutate(offer.id) });
            refresh();
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
        onAdded={() => {
          setDialog(null);
          changeView("pending");
          refresh();
        }}
      />
      <ImportJobBoardDialog open={dialog === "import"} onClose={() => setDialog(null)} />
      <PromoteDialog
        offer={promoting}
        onClose={() => setPromoting(null)}
        onPromoted={() => {
          if (promoting) leaveView(promoting.id);
          setPromoting(null);
          setNotice({ message: "Application created" });
          refresh();
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
