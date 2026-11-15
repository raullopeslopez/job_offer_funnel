import { DISCARD_REASON_LABELS } from "./discardReasons";
import type { Offer } from "./types";

export type DayGroup = "Today" | "Yesterday" | "Earlier";

const DAY_MS = 86_400_000;
const startOfDay = (date: Date) =>
  new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();

/** The group of the day an offer was added, in local time. */
export function dayGroup(createdAt: string, now: Date): DayGroup {
  const days = Math.round((startOfDay(now) - startOfDay(new Date(createdAt))) / DAY_MS);
  if (days <= 0) return "Today";
  return days === 1 ? "Yesterday" : "Earlier";
}

/** The items split into runs of the same title, in the same order. */
function groupInOrder<T>(items: T[], titleOf: (item: T) => string) {
  const groups: { title: string; offers: T[] }[] = [];
  for (const item of items) {
    const title = titleOf(item);
    const last = groups.at(-1);
    if (last?.title === title) last.offers.push(item);
    else groups.push({ title, offers: [item] });
  }
  return groups;
}

/** The offers, most recent first, split by the day they were added and in the same order. */
export function groupByDay<T extends { created_at: string }>(offers: T[], now: Date) {
  return groupInOrder(offers, (offer) => dayGroup(offer.created_at, now));
}

/** The group of an offer by the triager's verdict (specs/ui/inbox.feature). */
export function verdictGroup(offer: Pick<Offer, "triage" | "suggested_discard">): string {
  if (!offer.triage) return "Not triaged";
  if (offer.triage.verdict === "ok") return "AI: OK";
  return offer.suggested_discard
    ? `AI: KO · ${DISCARD_REASON_LABELS[offer.suggested_discard.reason]}`
    : "AI: KO";
}

/** The offers, as listed by verdict, split by their verdict group and in the same order. */
export function groupByVerdict<T extends Pick<Offer, "triage" | "suggested_discard">>(offers: T[]) {
  return groupInOrder(offers, verdictGroup);
}
