import { Box, Button, Link, Snackbar, Stack, Typography, useMediaQuery } from "@mui/material";
import {
  useInfiniteQuery,
  useIsMutating,
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { type KeyboardEvent, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router";
import { api } from "../../api/client";
import { SegmentedTabs } from "../../components/SegmentedTabs";
import { AddOfferDialog } from "./AddOfferDialog";
import { FrequentTitles } from "./FrequentTitles";
import { ImportJobBoardDialog } from "./ImportJobBoardDialog";
import { MaybeGroup, nearMissesQuery } from "./MaybeGroup";
import { NearMissGroups, nearMissGroupsQuery } from "./NearMissGroups";
import { OfferList } from "./OfferList";
import { PromoteDialog } from "./PromoteDialog";
import { isNearMiss, ReadingPane } from "./ReadingPane";
import { rowOrder } from "./rowOrder";
import { TriageButton, triageMutationKey } from "./TriageButton";
import { TriagerDiscardButton } from "./TriagerDiscardButton";
import { TriagerSuggestion } from "./TriagerSuggestion";
import type { Offer, OfferStatus, OfferView } from "./types";
import { groupVariants, variantKey } from "./variants";

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
// As many near misses as "Maybe" shows (MaybeGroup).
const MAYBE_SHOWN = 3;

type Notice = { message: string; undo?: () => void };

export function InboxPage() {
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const view = (params.get("status") as View | null) ?? "pending";
  const [dialog, setDialog] = useState<"add" | "import" | null>(null);
  const [promoting, setPromoting] = useState<Offer | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  // The offer open in the reading pane, and the roles whose variants are open in the list.
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [openVariants, setOpenVariants] = useState<string[]>([]);
  const isWide = useMediaQuery((theme) => theme.breakpoints.up("md"));
  const list = useRef<HTMLElement>(null);
  // The offer whose reasons to discard are open, and whether the focus follows the selection.
  const [discardingId, setDiscardingId] = useState<string | null>(null);
  const focusSelected = useRef(false);

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

  // The near misses of "Maybe" and of "One rule away" also open in the reading pane.
  const maybe = useQuery({ ...nearMissesQuery(MAYBE_SHOWN), enabled: view === "pending" });
  const nearMissGroups = useQuery({ ...nearMissGroupsQuery, enabled: view === "filtered" });

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
      openNextAfter(offerId);
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
      openNextAfter(offer.id);
      setNotice({ message: "Marked as rightly filtered", undo: () => unmark.mutate(offer.id) });
      refresh();
    },
  });

  const changeView = (next: View) => {
    setSelectedId(null);
    setOpenVariants([]);
    setParams(next === "pending" ? {} : { status: next });
  };

  const pages = offers.data?.pages ?? [];
  const items = pages.flatMap((page) => page.items);
  const listed = pages[0]?.total ?? 0;
  const viewIndex = VIEWS.findIndex(({ value }) => value === view);
  const total = counts[viewIndex]?.data ?? 0;
  const heading = VIEWS[viewIndex]?.heading;
  const triageRunning = useIsMutating({ mutationKey: triageMutationKey }) > 0;
  const context = { triageRunning, jobBoards: jobBoards.data ?? [], profiles: profiles.data ?? [] };

  // The offers of the view's rows; the selected one, or else the first of the view.
  const maybeItems = view === "pending" ? (maybe.data?.items ?? []) : [];
  const nearMissItems =
    view === "filtered" ? (nearMissGroups.data ?? []).flatMap((group) => group.offers) : [];
  const rowOffers = [...items, ...maybeItems, ...nearMissItems];
  // On a phone no offer is open until a row is tapped.
  const selected =
    rowOffers.find((o) => o.id === selectedId) ??
    (isWide ? (nearMissItems[0] ?? items[0] ?? maybeItems[0]) : undefined) ??
    null;
  // The rows as the list shows them, for "3 of 7" and for the offer that follows an action:
  // in Filtered the near-miss groups first, then the offers further away.
  const order =
    view === "pending"
      ? [...rowOrder(items, { byVerdict: true, variants: true, openVariants }), ...maybeItems]
      : [...nearMissItems, ...rowOrder(items, { single: view === "filtered" })];
  const orderIndex = order.findIndex((o) => o.id === selected?.id);
  const position = orderIndex < 0 ? undefined : { index: orderIndex, total: order.length };
  // After an action on an offer the next one opens, or the previous one if it was the last
  // (specs/ui/inbox.feature).
  // On a phone the screen goes back to the list instead.
  function openNextAfter(offerId: string) {
    if (!isWide) {
      setSelectedId(null);
      return;
    }
    const index = order.findIndex((o) => o.id === offerId);
    if (index < 0) return;
    focusSelected.current = true;
    setSelectedId((order[index + 1] ?? order[index - 1])?.id ?? null);
  }
  const selection = {
    selectedId: selected?.id ?? null,
    onSelect: (offer: Offer) => setSelectedId(offer.id),
  };
  // Keyboard triage on the focused list (specs/ui/inbox.feature): J/K move, P promotes, D opens
  // the reasons. Only on the selected row, so the arrows of the tabs are left alone.
  const onListKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    const target = event.target as HTMLElement;
    if (event.ctrlKey || event.metaKey || event.altKey || !selected) return;
    if (target.closest("input, textarea, select, [contenteditable]")) return;
    if (!target.closest("li") || target.getAttribute("aria-current") !== "true") return;
    const key = event.key.length === 1 ? event.key.toLowerCase() : event.key;
    const move = key === "j" || key === "ArrowDown" ? 1 : key === "k" || key === "ArrowUp" ? -1 : 0;
    if (move !== 0) {
      event.preventDefault();
      const next = order[orderIndex + move];
      if (!next) return;
      focusSelected.current = true;
      setSelectedId(next.id);
    } else if (key === "p" && selected.status === "pending") {
      setPromoting(selected);
    } else if (key === "d" && selected.status === "pending" && !isNearMiss(selected)) {
      setDiscardingId(selected.id);
    }
  };
  // The focus follows the selection after a key or an action, as the row it was on may be gone.
  const selectedKey = selected?.id;
  // biome-ignore lint/correctness/useExhaustiveDependencies: runs when the selection changes
  useEffect(() => {
    if (!focusSelected.current) return;
    const row = list.current?.querySelector<HTMLElement>('li button[aria-current="true"]');
    if (!row) return;
    focusSelected.current = false;
    row.focus({ preventScroll: true });
    if (isWide) row.scrollIntoView?.({ block: "nearest" });
  }, [selectedKey]);

  // The variants of the selected offer, when its row stands for them (specs/ui/inbox.feature).
  const run =
    view === "pending" && selected
      ? groupVariants(items).find(({ first }) => first.id === selected.id)
      : undefined;
  const variants =
    run && run.offers.length > 1
      ? {
          count: run.offers.length - 1,
          open: openVariants.includes(variantKey(run.first)),
          onToggle: () => {
            const key = variantKey(run.first);
            setOpenVariants((open) =>
              open.includes(key) ? open.filter((k) => k !== key) : [...open, key],
            );
          },
        }
      : undefined;

  // The four views: above the AI controls on a wide screen, under them on a phone.
  const viewTabs = (
    <Box sx={{ mt: 2 }}>
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
  );
  const readingPane = (
    <ReadingPane
      offer={selected}
      {...context}
      variants={variants}
      position={position}
      isDiscarding={selected?.id === discardingId}
      onDiscarding={(open) => setDiscardingId(open && selected ? selected.id : null)}
      onBack={isWide ? undefined : () => setSelectedId(null)}
      onDiscarded={(offer) => {
        setDiscardingId(null);
        openNextAfter(offer.id);
        leaveView(offer.id);
        setNotice({ message: "Offer discarded", undo: () => restore.mutate(offer.id) });
        refresh();
      }}
      onPromote={setPromoting}
      onRestore={(offer) => restore.mutate(offer.id)}
      onRightlyFiltered={(offer) => markRightlyFiltered.mutate(offer)}
    />
  );

  return (
    <>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "minmax(0, 1fr)", md: "minmax(420px, 520px) minmax(0, 1fr)" },
          alignItems: "start",
        }}
      >
        <Box
          component="section"
          aria-label="Offer list"
          inert={!isWide && selected !== null}
          ref={list}
          onKeyDown={onListKeyDown}
          sx={{ minWidth: 0, borderRight: { md: 1 }, borderColor: { md: "divider" } }}
        >
          <Box sx={{ px: 2, pb: 1 }}>
            <Stack
              direction="row"
              spacing={2}
              useFlexGap
              sx={{ alignItems: "baseline", flexWrap: "wrap", justifyContent: "space-between" }}
            >
              <Stack direction="row" spacing={1.5} sx={{ alignItems: "baseline" }}>
                <Typography variant="h4" component="h1">
                  Inbox
                </Typography>
                <Typography color="text.secondary">
                  {total} {heading}
                </Typography>
              </Stack>
              <Stack direction="row" spacing={2}>
                <Link component="button" type="button" onClick={() => setDialog("import")}>
                  Import job board
                </Link>
                <Link component="button" type="button" onClick={() => setDialog("add")}>
                  Add offer
                </Link>
              </Stack>
            </Stack>

            {!isWide && viewTabs}
            {view === "pending" && (
              <Stack
                spacing={0.5}
                useFlexGap
                sx={{ mt: 1.5, "& .MuiButton-root": { whiteSpace: "nowrap" } }}
              >
                <TriageButton running={triageRunning} />
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
              </Stack>
            )}

            {view === "pending" && (
              <Box sx={{ mt: 2 }}>
                <TriagerSuggestion />
              </Box>
            )}

            {isWide && viewTabs}
          </Box>

          {view === "filtered" && <NearMissGroups {...context} {...selection} />}
          {view === "filtered" && (
            <Box sx={{ px: 2 }}>
              <FrequentTitles profiles={context.profiles} />
            </Box>
          )}

          {offers.isSuccess && (view !== "filtered" || listed > 0 || total === 0) && (
            <OfferList
              view={view}
              offers={items}
              {...context}
              {...selection}
              single={view === "filtered" ? { title: "Further away", count: listed } : undefined}
              byVerdict={view === "pending"}
              variants={view === "pending"}
              openVariants={openVariants}
            />
          )}

          {offers.hasNextPage && (
            <Box sx={{ display: "flex", justifyContent: "center", my: 3 }}>
              <Button
                variant="outlined"
                loading={offers.isFetchingNextPage}
                onClick={() => offers.fetchNextPage()}
              >
                Show more
              </Button>
            </Box>
          )}

          {view === "pending" && <MaybeGroup {...context} {...selection} />}

          {(view === "pending" || view === "filtered") && (
            <Typography
              variant="caption"
              component="p"
              color="text.secondary"
              sx={{ display: { xs: "none", md: "block" }, px: 2, py: 2 }}
            >
              J/K move · P promote · D discard
            </Typography>
          )}
        </Box>

        {isWide ? (
          <Box
            component="section"
            aria-label="Reading pane"
            sx={{
              minWidth: 0,
              px: 5,
              pt: 1,
              display: "flex",
              flexDirection: "column",
              minHeight: "70vh",
              // The pane stays in view while the list scrolls.
              position: "sticky",
              top: 0,
              maxHeight: "100vh",
              overflowY: "auto",
            }}
          >
            {readingPane}
          </Box>
        ) : (
          readingPane
        )}
      </Box>

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
          if (promoting) {
            openNextAfter(promoting.id);
            leaveView(promoting.id);
          }
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
