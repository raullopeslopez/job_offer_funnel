import type { components } from "../../api/schema";
import { RuleCell } from "../../components/RuleCell";
import { MergedRuleCell, RuleStrip } from "../../components/RuleStrip";
import { MODES, stackCell } from "./filterRules";

type Reading = components["schemas"]["ReadingRead"];

const cell = (value: string | null) =>
  value ? ({ value, state: "pass" } as const) : ({ state: "unknown" } as const);

export function location({ admits_location, location }: Reading): string | null {
  if (admits_location === null) return null;
  return admits_location ? (location ?? "Yes") : `Not from ${location}`;
}

export function contract({ stable }: Reading): string | null {
  if (stable === null) return null;
  return stable ? "Stable" : "Not stable";
}

function role({ engineering }: Reading): string | null {
  if (engineering === null) return null;
  return engineering ? "Engineering" : "Not engineering";
}

// What the description of an offer says of the mode, the location, the contract, the role
// and the stack.
export function ReadingStrip({ readings }: { readings: Reading[] }) {
  const reading = readings[0];
  if (!reading) {
    return (
      <RuleStrip>
        <MergedRuleCell>Not read yet, or no description to read</MergedRuleCell>
      </RuleStrip>
    );
  }
  return (
    <RuleStrip>
      <RuleCell label="Mode" {...cell(reading.work_mode && MODES[reading.work_mode])} />
      <RuleCell label="Location" {...cell(location(reading))} />
      <RuleCell label="Contract" {...cell(contract(reading))} />
      <RuleCell label="Role" {...cell(role(reading))} />
      <RuleCell {...stackCell(readings)} />
    </RuleStrip>
  );
}
