import { Typography } from "@mui/material";
import { RuleCell } from "../../components/RuleCell";
import { MergedRuleCell, RuleStrip } from "../../components/RuleStrip";
import type { Source } from "../../theme";
import { type Cell, ruleCells, type SearchProfile } from "./filterRules";
import { ReadingStrip } from "./ReadingStrip";
import type { Offer } from "./types";

type Props = { offer: Offer; sourceKind: Source; profiles: SearchProfile[] };

const UNKNOWN = "Mode, location, contract, role and stack unknown";
// The cells a reading fills: Mode, Location, Contract, Role and Stack.
const READ_CELLS = 5;

const NOTHING_TO_READ: Partial<Record<Source, string>> = {
  email: `${UNKNOWN}: email alerts arrive without a description to read`,
  manual: `${UNKNOWN}: you added it by hand`,
};

const nothingToRead = (kind: Source) =>
  NOTHING_TO_READ[kind] ?? `${UNKNOWN}: the offer has no description to read`;

/** The evidence of a failed rule, the literal sentence of the description, in quotes. */
export function Evidence({ cells }: { cells: Cell[] }) {
  const evidence = cells.find((cell) => cell.state === "failed")?.evidence;
  if (!evidence) return null;
  return (
    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
      “{evidence}”
    </Typography>
  );
}

// The strip of an offer: its rules and stack when it has a filter reason, or else what its
// reading says (specs/ui/inbox.feature).
export function OfferStrip({ offer, sourceKind, profiles }: Props) {
  const reason = offer.filter_reason;
  if (!reason) {
    if (sourceKind === "manual" && offer.readings.length === 0) {
      return (
        <RuleStrip>
          <MergedRuleCell span={READ_CELLS}>{nothingToRead("manual")}</MergedRuleCell>
        </RuleStrip>
      );
    }
    return <ReadingStrip readings={offer.readings} />;
  }
  const profile = profiles.find((p) => p.id === reason.search_profile_id);
  const cells = ruleCells(reason, offer.readings, profile);
  const shown = reason.has_description ? cells : cells.slice(0, 2);
  return (
    <>
      <RuleStrip>
        {shown.map((cell) => (
          <RuleCell key={cell.label} label={cell.label} value={cell.value} state={cell.state} />
        ))}
        {!reason.has_description && (
          <MergedRuleCell span={READ_CELLS}>{nothingToRead(sourceKind)}</MergedRuleCell>
        )}
      </RuleStrip>
      <Evidence cells={cells} />
    </>
  );
}
