// Helpers shared by the steps of every screen.

// Spec field names → labels in the app's forms.
const FIELD_LABELS: Record<string, string> = {
  url: "URL",
  company: "Company",
  title: "Title",
  notes: "Notes",
  name: "Name",
  titles: "Titles",
  keywords: "Keywords",
  excluded_keywords: "Excluded keywords",
  location: "Location",
  work_modes: "Work modes",
  role: "Role",
  channel: "Channel",
  priority: "Priority",
  stage: "Stage",
  occurred_on: "Start date",
  website: "Website",
  search_url_template: "Search URL template",
  syntax: "Syntax",
};

export const fieldLabel = (field: string) => FIELD_LABELS[field] ?? field;

// A list like `"C", "B", "A"` is not one {string}: steps match the whole quoted list.
export const quoted = (list: string) =>
  [...list.matchAll(/"([^"]*)"/g)].map((match) => match[1] ?? "");

// A spec list value: `"remote, hybrid"` → `["remote", "hybrid"]`.
export const commaList = (value: string) =>
  value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
