import type { components } from "../../api/schema";
import type { RuleState } from "../../components/RuleCell";

type FilterReason = components["schemas"]["FilterReasonRead"];
type RuleRead = components["schemas"]["RuleRead"];
type Rule = components["schemas"]["Rule"];
type WorkMode = components["schemas"]["WorkMode"];
export type SearchProfile = components["schemas"]["SearchProfileRead"];

export const MODES: Record<WorkMode, string> = {
  remote: "Remote",
  hybrid: "Hybrid",
  onsite: "On-site",
};

/** One cell of the strip: a rule of the profile and what the offer gave for it. */
export type Cell = { label: string; state: RuleState; value?: string; evidence?: string | null };

type ReadRule = Exclude<Rule, "title" | "excluded">;

const LABELS: Record<ReadRule, string> = {
  keywords: "Keywords",
  work_mode: "Mode",
  location: "Location",
  stable: "Contract",
};

const mode = (value: RuleRead["value"]) => MODES[value as WorkMode] ?? "—";

// The value of a rule that passed or failed, against what the profile asks.
function ruleValue({ rule, result, found, missing, value }: RuleRead, profile?: SearchProfile) {
  const passed = result === "passed";
  switch (rule) {
    case "keywords":
      return passed ? found.join(", ") : `Missing: ${missing.join(", ")}`;
    case "work_mode": {
      const asked = (profile?.work_modes ?? []).map((m) => MODES[m]).join(" or ");
      return passed ? mode(value) : `${mode(value)}, you ask ${asked}`;
    }
    case "location":
      return passed
        ? (profile?.location ?? "Yes")
        : `Not from ${profile?.location ?? "your location"}`;
    default:
      return passed ? "Stable" : "Not stable";
  }
}

// The title and the excluded keywords share the Title cell: both are about the words of the title.
function titleCell(rules: RuleRead[]): Cell {
  const title = rules.find((r) => r.rule === "title");
  const excluded = rules.find((r) => r.rule === "excluded");
  if (title?.result === "failed") {
    return { label: "Title", state: "failed", value: "No title of yours" };
  }
  if (excluded?.result === "failed") {
    return { label: "Title", state: "failed", value: `"${excluded.found[0]}", you exclude it` };
  }
  return { label: "Title", state: "pass", value: title?.found[0] };
}

function ruleCell(name: ReadRule, rules: RuleRead[], profile?: SearchProfile): Cell {
  const label = LABELS[name];
  const found = rules.find((r) => r.rule === name);
  if (!found) return { label, state: "pass", value: "Any" };
  if (found.result === "unknown") return { label, state: "unknown" };
  const failed = found.result === "failed";
  return {
    label,
    state: failed ? "failed" : "pass",
    value: ruleValue(found, profile),
    evidence: failed ? found.evidence : null,
  };
}

/** The five cells of an offer's filter reason: Title, Keywords, Mode, Location, Contract. */
export function ruleCells(reason: FilterReason, profile?: SearchProfile): Cell[] {
  return [
    titleCell(reason.rules),
    ...(Object.keys(LABELS) as ReadRule[]).map((name) => ruleCell(name, reason.rules, profile)),
  ];
}

/** The groups of near misses, one per rule that can filter an offer whose title passes. */
export const NEAR_MISS_GROUPS: { rule: Exclude<Rule, "title">; label: string }[] = [
  { rule: "excluded", label: "A word you exclude" },
  { rule: "keywords", label: "A keyword missing" },
  { rule: "work_mode", label: "Mode" },
  { rule: "location", label: "Location" },
  { rule: "stable", label: "Not stable" },
];

// What a failed rule is about, to break a group down: the word or the value behind it.
function breakdownKeys({ rule, found, missing, value }: RuleRead, profile?: SearchProfile) {
  if (rule === "excluded") return found;
  if (rule === "keywords") return missing;
  if (rule === "work_mode") return [mode(value)];
  if (rule === "location") return profile?.location ? [profile.location] : [];
  return [];
}

type ReasonOf = { filter_reason: FilterReason | null };

/** "Junior 2 · Intern 1": how many near misses failing `rule` fail it for each word or value. */
export function breakdown(offers: ReasonOf[], rule: Rule, profiles: SearchProfile[]): string {
  const counts = new Map<string, number>();
  for (const { filter_reason: reason } of offers) {
    const failed = reason?.rules.find((r) => r.rule === rule && r.result === "failed");
    if (!(reason && failed)) continue;
    const profile = profiles.find((p) => p.id === reason.search_profile_id);
    for (const key of breakdownKeys(failed, profile)) counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return [...counts]
    .sort(([a, x], [b, y]) => y - x || a.localeCompare(b))
    .map(([key, count]) => `${key} ${count}`)
    .join(" · ");
}
