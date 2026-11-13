import type { components } from "../../api/schema";
import { RuleCell } from "../../components/RuleCell";
import { MergedRuleCell, RuleStrip } from "../../components/RuleStrip";

type Reading = components["schemas"]["ReadingRead"];
type WorkMode = components["schemas"]["WorkMode"];

const MODES: Record<WorkMode, string> = { remote: "Remote", hybrid: "Hybrid", onsite: "On-site" };

const cell = (value: string | null) =>
  value ? ({ value, state: "pass" } as const) : ({ state: "unknown" } as const);

function location({ admits_location, location }: Reading): string | null {
  if (admits_location === null) return null;
  return admits_location ? (location ?? "Yes") : `Not from ${location}`;
}

function contract({ stable }: Reading): string | null {
  if (stable === null) return null;
  return stable ? "Stable" : "Not stable";
}

// What the description of an offer says of the mode, the location and the contract.
export function ReadingStrip({ readings }: { readings: Reading[] }) {
  const reading = readings[0];
  if (!reading) {
    return (
      <RuleStrip>
        <MergedRuleCell span={3}>Not read yet, or no description to read</MergedRuleCell>
      </RuleStrip>
    );
  }
  return (
    <RuleStrip>
      <RuleCell label="Mode" {...cell(reading.work_mode && MODES[reading.work_mode])} />
      <RuleCell label="Location" {...cell(location(reading))} />
      <RuleCell label="Contract" {...cell(contract(reading))} />
    </RuleStrip>
  );
}
