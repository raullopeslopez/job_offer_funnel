---
paths:
  - "specs/**"
---

# Specs (Gherkin)

- **Specs are written entirely in English**, like the code and the app. Internationalisation is a future feature, not a reason to write specs in another language.
- Before writing a spec, read `docs/funnel.md` (behaviour of each stage) and `docs/glossary.md` (use the EN column: `applied`, `offer_declined`...).
- English Gherkin keywords, with no `# language:` header: `Feature`, `Background`, `Scenario`, `Scenario Outline`, `Examples`, `Given`, `When`, `Then`, `And`.
- Path: `specs/<module>/<name>.feature`, with the module name in snake_case.
- Describe behaviour observable from the outside (what happens), never the implementation (tables, classes, endpoints).
- One `When` per scenario.
- Cases that differ only in data: `Scenario Outline` + `Examples`, not copied scenarios.
- Gherkin trims table cells: values whose surrounding spaces matter (`"   "`, `"  Acme  "`) go in the step text of their own scenario, never in an `Examples` cell.
- If a term is missing from the glossary, add it there first.
- Include the error paths (invalid transition, missing resource), not just the happy path.
- A new or changed spec always goes through the user's review before implementation.
