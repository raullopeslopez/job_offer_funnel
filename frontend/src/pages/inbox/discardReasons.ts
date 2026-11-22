import type { components } from "../../api/schema";
import type { Offer } from "./types";

export type DiscardReason = components["schemas"]["DiscardReason"];

export const DISCARD_REASON_LABELS: Record<DiscardReason, string> = {
  title_word: "A word in the title",
  stack: "Stack",
  location: "Location",
  contract: "Contract",
  company: "Company",
  none: "No reason",
  expired: "Expired",
};

/** The reasons the user can choose, in the order of the piece; "expired" only the imports set. */
export const CHOSEN_REASONS: DiscardReason[] = [
  "title_word",
  "stack",
  "location",
  "contract",
  "company",
  "none",
];

/** The words of a title as the piece offers them: split by spaces, without the punctuation around. */
export function titleWords(title: string): string[] {
  const words = title
    .split(/\s+/)
    .map((word) => word.replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}+#]+$/gu, ""))
    .filter(Boolean);
  return [...new Set(words)];
}

/** The reason of a discard, with its word: "Contract", "A word in the title: Lead". */
export function discardReason(offer: Pick<Offer, "discard_reason" | "discard_word">): string {
  if (!offer.discard_reason) return "—";
  const label = DISCARD_REASON_LABELS[offer.discard_reason];
  return offer.discard_word ? `${label}: ${offer.discard_word}` : label;
}

/** What a discarded piece says of its reason, and whether the AI discarded it
 * (specs/inbox/triager_discards.feature). */
export function discardReasonText(
  offer: Pick<Offer, "discard_reason" | "discard_word" | "triager_discard">,
): string {
  if (!offer.discard_reason) return "—";
  const reason = discardReason(offer);
  return offer.triager_discard === "discarded" ? `Discarded by AI · ${reason}` : reason;
}
