import { Box, Button, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../api/client";
import { Count, GroupHeader } from "../../components/GroupedList";
import { offerSourceKind } from "../../components/offerSource";
import { breakdown, NEAR_MISS_GROUPS } from "./filterRules";
import type { OfferContext, RowSelection } from "./OfferList";
import { OfferRow } from "./OfferRow";
import type { Offer } from "./types";

// Enough to break a group down exactly while it has no more near misses than this.
const GROUP_LIMIT = 100;

export const nearMissGroupsQuery = {
  queryKey: ["offers", "near-miss-groups"],
  queryFn: async () => {
    const { data, error } = await api.GET("/api/v1/offers/near-misses", {
      params: { query: { limit: GROUP_LIMIT } },
    });
    if (error) throw error;
    return data.groups;
  },
};

type Props = OfferContext & RowSelection;

// "One rule away": the near misses grouped by the rule that filtered them, in one request.
export function NearMissGroups({ selectedId, onSelect, ...context }: Props) {
  const groups = useQuery(nearMissGroupsQuery).data ?? [];
  const byRule = new Map(groups.map((group) => [group.rule, group]));
  const total = groups.reduce((sum, group) => sum + group.total, 0);
  if (total === 0) return null;
  return (
    <Box component="section" aria-label="One rule away">
      <GroupHeader title="One rule away" count={total} />
      {NEAR_MISS_GROUPS.map(({ rule, label }) => {
        const page = byRule.get(rule);
        if (!page) return null;
        return (
          <NearMissGroup
            key={rule}
            label={label}
            total={page.total}
            breakdown={breakdown(page.offers, rule, context.profiles)}
            offers={page.offers}
            context={context}
            selection={{ selectedId, onSelect }}
          />
        );
      })}
    </Box>
  );
}

type GroupProps = {
  label: string;
  total: number;
  breakdown: string;
  offers: Offer[];
  context: OfferContext;
  selection: RowSelection;
};

// A rule and how many near misses it filtered, closed until shown; open, its rows.
function NearMissGroup({ label, total, breakdown, offers, context, selection }: GroupProps) {
  const [open, setOpen] = useState(false);
  return (
    <Box component="section" aria-label={label} sx={{ borderBottom: 1, borderColor: "divider" }}>
      <Stack direction="row" spacing={2} sx={{ alignItems: "center", px: 2, py: 1.5 }}>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="subtitle1" component="h3" sx={{ fontWeight: 600 }}>
            {label} · <Count value={total} />
          </Typography>
          {breakdown && (
            <Typography variant="body2" color="text.secondary">
              {breakdown}
            </Typography>
          )}
        </Box>
        <Button aria-expanded={open} onClick={() => setOpen(!open)}>
          {open ? "Hide" : "Show"}
        </Button>
      </Stack>
      {open && (
        <Box
          component="ul"
          sx={{ listStyle: "none", m: 0, p: 0, borderTop: 1, borderColor: "divider" }}
        >
          {offers.map((offer) => (
            <OfferRow
              key={offer.id}
              offer={offer}
              sourceKind={offerSourceKind(offer, context.jobBoards)}
              selected={offer.id === selection.selectedId}
              onSelect={selection.onSelect}
              indented
              now={context.now}
            />
          ))}
        </Box>
      )}
    </Box>
  );
}
