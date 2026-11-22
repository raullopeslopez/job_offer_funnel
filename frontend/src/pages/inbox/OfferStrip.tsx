import { RuleCell } from "../../components/RuleCell";
import { MergedRuleCell, RuleStrip } from "../../components/RuleStrip";
import type { Source } from "../../theme";
import { ruleCells, type SearchProfile } from "./filterRules";
import { ReadingStrip } from "./ReadingStrip";
import type { Offer } from "./types";

type Props = { offer: Offer; sourceKind: Source; profiles: SearchProfile[] };

const UNKNOWN = "Mode, location, contract, role and stack unknown";

const NOTHING_TO_READ: Partial<Record<Source, string>> = {
  email: `${UNKNOWN}: email alerts arrive without a description to read`,
  manual: `${UNKNOWN}: you added it by hand`,
};

const nothingToRead = (kind: Source) =>
  NOTHING_TO_READ[kind] ?? `${UNKNOWN}: the offer has no description to read`;

// The rules of an offer: its rules and stack when it has a filter reason, with the evidence of
// the rule that filtered it under its cell, or else what its reading says
// (specs/ui/inbox.feature).
export function OfferStrip({ offer, sourceKind, profiles }: Props) {
  const reason = offer.filter_reason;
  if (!reason) {
    if (sourceKind === "manual" && offer.readings.length === 0) {
      return (
        <RuleStrip>
          <MergedRuleCell>{nothingToRead("manual")}</MergedRuleCell>
        </RuleStrip>
      );
    }
    return <ReadingStrip readings={offer.readings} />;
  }
  const profile = profiles.find((p) => p.id === reason.search_profile_id);
  const cells = ruleCells(reason, offer.readings, profile);
  const shown = reason.has_description ? cells : cells.slice(0, 2);
  return (
    <RuleStrip>
      {shown.map((cell) => (
        <RuleCell key={cell.label} {...cell} />
      ))}
      {!reason.has_description && <MergedRuleCell>{nothingToRead(sourceKind)}</MergedRuleCell>}
    </RuleStrip>
  );
}
