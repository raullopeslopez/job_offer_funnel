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

/** The offers, most recent first, split by the day they were added and in the same order. */
export function groupByDay<T extends { created_at: string }>(
  offers: T[],
  now: Date,
): { title: DayGroup; offers: T[] }[] {
  const groups: { title: DayGroup; offers: T[] }[] = [];
  for (const offer of offers) {
    const title = dayGroup(offer.created_at, now);
    const last = groups.at(-1);
    if (last?.title === title) last.offers.push(offer);
    else groups.push({ title, offers: [offer] });
  }
  return groups;
}
