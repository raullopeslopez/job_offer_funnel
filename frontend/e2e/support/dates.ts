// Dates of the specs, shared by the steps of every screen.

// `YYYY-MM-DD` of a spec date: an ISO date, "today", "tomorrow" or "<n> days ago".
export function isoDate(value: string): string {
  const daysAgo =
    value === "today" ? 0 : value === "tomorrow" ? -1 : Number(/^(\d+) days ago$/.exec(value)?.[1]);
  if (Number.isNaN(daysAgo)) return value;
  const date = new Date();
  date.setDate(date.getDate() - daysAgo);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

// The app shows dates in this format (the history of the detail).
const dateFormat = new Intl.DateTimeFormat("en", { dateStyle: "medium", timeZone: "UTC" });
export const shownDate = (iso: string) => (iso ? dateFormat.format(new Date(iso)) : "");
