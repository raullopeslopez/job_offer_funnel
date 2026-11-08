import type { components } from "../../api/schema";

type Schemas = components["schemas"];
export type Application = Schemas["ApplicationRead"];
export type Stage = Schemas["Stage"];
export type Outcome = Schemas["Outcome"];
export type Channel = Schemas["Channel"];
export type Priority = Schemas["Priority"];

// The values the API accepts, in the order of the funnel (docs/funnel.md).
export const STAGES: Stage[] = [
  "evaluated",
  "applied",
  "screening",
  "interviewing",
  "offer",
  "accepted",
];
export const OUTCOMES: Outcome[] = ["rejected", "ghosted", "withdrawn", "offer_declined"];
export const CHANNELS: Channel[] = [
  "portal",
  "referral",
  "recruiter_inbound",
  "direct",
  "networking",
];
export const PRIORITIES: Priority[] = ["high", "medium", "low"];

const dateFormat = new Intl.DateTimeFormat("en", { dateStyle: "medium", timeZone: "UTC" });
/** A `YYYY-MM-DD` date or a timestamp, as the app shows it. */
export const formatDate = (value: string) => dateFormat.format(new Date(value));
