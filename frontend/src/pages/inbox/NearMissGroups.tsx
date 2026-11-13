import { Box, Button, Link, Stack, Typography } from "@mui/material";
import { useQueries, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../api/client";
import { GroupedList } from "../../components/GroupedList";
import { offerSourceKind } from "../../components/offerSource";
import { RuleCell } from "../../components/RuleCell";
import { SourceTag } from "../../components/SourceTag";
import { mono, offerShape } from "../../theme";
import { breakdown, NEAR_MISS_GROUPS, ruleCells } from "./filterRules";
import { type NearMissActions, NearMissButtons, nearMissesQuery } from "./MaybeGroup";
import type { OfferContext } from "./OfferList";
import { Evidence } from "./OfferStrip";
import type { Offer } from "./types";

// Enough to break a group down exactly while it has no more near misses than this.
const GROUP_LIMIT = 100;

export const filteredCountsQuery = {
  queryKey: ["offers", "filtered-counts"],
  queryFn: async () => {
    const { data, error } = await api.GET("/api/v1/offers/filtered-counts");
    if (error) throw error;
    return data;
  },
};

type Props = OfferContext & NearMissActions;

// "One rule away": the near misses grouped by the rule that filtered them.
export function NearMissGroups({ onPromote, onRightlyFiltered, ...context }: Props) {
  const counts = useQuery(filteredCountsQuery);
  const groups = useQueries({
    queries: NEAR_MISS_GROUPS.map(({ rule }) => nearMissesQuery(GROUP_LIMIT, rule)),
  });
  const total = counts.data?.near_misses ?? 0;
  if (total === 0) return null;
  return (
    <Box sx={{ mb: 4 }}>
      <GroupedList title="One rule away" count={total}>
        {NEAR_MISS_GROUPS.map(({ rule, label }, index) => {
          const page = groups[index]?.data;
          if (!page || page.total === 0) return null;
          return (
            <NearMissGroup
              key={rule}
              label={label}
              total={page.total}
              breakdown={breakdown(page.items, rule, context.profiles)}
              offers={page.items}
              context={context}
              actions={{ onPromote, onRightlyFiltered }}
            />
          );
        })}
      </GroupedList>
    </Box>
  );
}

type GroupProps = {
  label: string;
  total: number;
  breakdown: string;
  offers: Offer[];
  context: OfferContext;
  actions: NearMissActions;
};

function NearMissGroup({ label, total, breakdown, offers, context, actions }: GroupProps) {
  const [open, setOpen] = useState(false);
  return (
    <Box
      component="section"
      aria-label={label}
      sx={{ p: 2, bgcolor: "background.paper", border: 1, borderColor: "divider" }}
    >
      <Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="subtitle1" component="h3" sx={{ fontWeight: 600 }}>
            {label} ·{" "}
            <Box component="span" sx={{ fontFamily: mono, fontWeight: 500 }}>
              {total}
            </Box>
          </Typography>
          {breakdown && (
            <Typography variant="body2" color="text.secondary">
              {breakdown}
            </Typography>
          )}
        </Box>
        <Button variant="outlined" aria-expanded={open} onClick={() => setOpen(!open)}>
          {open ? "Hide" : "Show"}
        </Button>
      </Stack>
      {open && (
        <Stack spacing={1} sx={{ mt: 2 }}>
          {offers.map((offer) => (
            <NearMissRow key={offer.id} offer={offer} context={context} actions={actions} />
          ))}
        </Stack>
      )}
    </Box>
  );
}

type RowProps = { offer: Offer; context: OfferContext; actions: NearMissActions };

// A near miss in a compact row: its source, title and company, the cell of its rule.
function NearMissRow({ offer, context, actions }: RowProps) {
  const reason = offer.filter_reason;
  const profile = context.profiles.find((p) => p.id === reason?.search_profile_id);
  const cells = reason ? ruleCells(reason, profile) : [];
  const failed = cells.find((cell) => cell.state === "failed");
  const sourceKind = offerSourceKind(offer, context.jobBoards);
  return (
    <Box
      component="article"
      aria-label={offer.title}
      sx={{ p: 1.5, bgcolor: "fill", borderRadius: offerShape.pieceRadius }}
    >
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={2}
        sx={{ alignItems: { sm: "center" } }}
      >
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <SourceTag
            kind={sourceKind}
            name={sourceKind === "watched" ? undefined : offer.job_board_name}
          />
          <Typography variant="body1" sx={{ mt: 0.5, fontWeight: 600 }}>
            <Link href={offer.url} target="_blank" rel="noopener noreferrer" color="inherit">
              {offer.title}
            </Link>
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {offer.company}
          </Typography>
        </Box>
        {failed && (
          <Box sx={{ width: { sm: 1 / 3 } }}>
            <RuleCell label={failed.label} value={failed.value} state={failed.state} />
          </Box>
        )}
        <Stack direction="row" spacing={1}>
          <NearMissButtons offer={offer} {...actions} />
        </Stack>
      </Stack>
      <Evidence cells={cells} />
    </Box>
  );
}
