import { groupByDay, groupByVerdict } from "./dayGroups";
import type { Offer } from "./types";
import { groupVariants, variantKey } from "./variants";

type Options = {
  single?: boolean;
  byVerdict?: boolean;
  variants?: boolean;
  openVariants?: string[];
  now?: Date;
};

/** The offers in the order `OfferList` shows their rows: by group, with closed variants left out. */
export function rowOrder(
  offers: Offer[],
  { single, byVerdict, variants, openVariants = [], now = new Date() }: Options,
): Offer[] {
  const rows = (listed: Offer[]) =>
    variants
      ? groupVariants(listed).flatMap(({ first, offers: run }) =>
          openVariants.includes(variantKey(first)) ? run : [first],
        )
      : listed;
  if (single) return rows(offers);
  const groups =
    byVerdict && offers.some((offer) => offer.triage)
      ? groupByVerdict(offers)
      : groupByDay(offers, now);
  return groups.flatMap((group) => rows(group.offers));
}
