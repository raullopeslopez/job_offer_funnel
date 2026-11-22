import type { Source, Tone } from "../../theme";
import { discardReason } from "./discardReasons";
import { MODES, ruleCells, type SearchProfile } from "./filterRules";
import { contract, location } from "./ReadingStrip";
import type { Offer } from "./types";

/** What a row says of its offer: a label (text, never only color) and one line. */
export type RowLine = { label: string; tone: Tone; line: string };

const CONFIDENCE = { low: "Low", medium: "Medium", high: "High" } as const;

const NOTHING_TO_READ: Partial<Record<Source, string>> = {
  email: "Nothing to read: email alert",
  manual: "Nothing to read: added by hand",
};

// What the reading of a pending offer says: mode, location, contract and stack, or why there
// is nothing to read.
function readingLine(offer: Offer, sourceKind: Source): string {
  const reading = offer.readings[0];
  if (!reading) {
    const noDescription = !offer.filter_reason?.has_description;
    return (noDescription && NOTHING_TO_READ[sourceKind]) || "Not read yet";
  }
  const stack = reading.stack.join(", ");
  const parts = [
    reading.work_mode && MODES[reading.work_mode],
    location(reading),
    contract(reading),
    stack,
  ].filter(Boolean);
  return parts.length > 0 ? parts.join(" · ") : "Nothing stated yet";
}

// The rule that filtered a filtered offer, as its failed cell says it.
function failedLine(offer: Offer, profiles: SearchProfile[]): string {
  const reason = offer.filter_reason;
  if (!reason) return "";
  const profile = profiles.find((p) => p.id === reason.search_profile_id);
  const failed = ruleCells(reason, offer.readings, profile).find((c) => c.state === "failed");
  return failed ? `${failed.label}: ${failed.value}` : "";
}

/** The label and the line of the row of an offer (specs/ui/inbox.feature). */
export function rowLine(offer: Offer, sourceKind: Source, profiles: SearchProfile[]): RowLine {
  if (offer.status === "promoted") {
    return { label: "Promoted", tone: "green", line: "Application created" };
  }
  if (offer.status === "discarded") {
    return {
      label: offer.triager_discard === "discarded" ? "Discarded by AI" : "Discarded",
      tone: "neutral",
      line: discardReason(offer),
    };
  }
  const triage = offer.triage;
  const ai = triage
    ? `AI: ${triage.verdict.toUpperCase()}${triage.confidence ? ` · ${CONFIDENCE[triage.confidence]}` : ""}`
    : "";
  const isOk = triage?.verdict === "ok";
  if (offer.filtered) {
    const near = offer.filter_reason?.near_miss === true;
    return {
      label: isOk ? ai : near ? "Near miss" : "Filtered",
      tone: isOk ? "green" : near ? "amber" : "neutral",
      line: failedLine(offer, profiles),
    };
  }
  if (triage) {
    const why = isOk ? (triage.why_yes ?? triage.why_not) : (triage.why_not ?? triage.why_yes);
    return { label: ai, tone: isOk ? "green" : "red", line: why?.why ?? "" };
  }
  return { label: "Not triaged", tone: "neutral", line: readingLine(offer, sourceKind) };
}
