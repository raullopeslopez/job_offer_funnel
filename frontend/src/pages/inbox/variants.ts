import type { Offer } from "./types";

type Variant = Pick<Offer, "company" | "base_title">;

/** What the variants of the same role share: their company and their base title. */
export const variantKey = (offer: Variant) => `${offer.company}|${offer.base_title}`.toLowerCase();

/** The offers split into runs of variants of the same role, in the same order. */
export function groupVariants<T extends Variant>(offers: T[]) {
  const runs: { first: T; offers: T[] }[] = [];
  for (const offer of offers) {
    const last = runs.at(-1);
    if (last && variantKey(last.first) === variantKey(offer)) last.offers.push(offer);
    else runs.push({ first: offer, offers: [offer] });
  }
  return runs;
}

/** "1 more variant of this role", "2 more variants of this role". */
export function moreVariantsOfRole(count: number): string {
  return `${count} more ${count === 1 ? "variant" : "variants"} of this role`;
}
