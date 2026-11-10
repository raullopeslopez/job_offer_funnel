# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
While the version is `0.x`, the API may change without a major version bump.

## [Unreleased]

### Added

- Filtered offers: a pending imported offer that fits none of the search profiles is
  `filtered` (new field on every offer), so a badly written profile hides offers instead
  of losing them. It always follows the current profiles: creating, editing or deleting
  one changes it at once. List them with `GET /api/v1/offers?filtered=true` (or `false`
  for the others); they can still be discarded or promoted. The inbox screen shows them
  in their own Filtered tab.

- Scheduled imports: on the deployed app the inbox fills by itself every 6 hours with the
  offers of every public feed and watched company (GitHub Actions workflow
  `import-offers`, also runnable by hand). `just import-offers` does the same against the
  local API, or any API given in `API_URL`.

- The app can be deployed to Render (API and web app, `render.yaml`) with the database in Neon.
- Web app navigation with an icon per screen, a light/dark theme toggle that remembers your choice, and a mobile layout below 900px with a top bar and a slide-in menu.
- `just seed-job-boards` now registers 43 more job boards with a checked search URL:
  remote boards (Remote OK, Remotive, Remote.co, FlexJobs, RemoteJobs.io, EuRemoteJobs…),
  UK and European boards (Reed, Totaljobs, CWJobs, CV-Library, Adzuna, Indeed UK, jobtensor,
  Landing.jobs…), tech and startup boards (Levels.fyi, Built In, Startup Jobs, Hiring Cafe…)
  and diversity boards (Women in Tech Jobs, Evenbreak…).
- `just seed-job-boards` also registers the job search of five tech recruitment agencies:
  Client Server, Understanding Recruitment, Hunter Bond, 3Search and Durlston Partners.
- New look for the web app: serif titles, a refreshed palette and status colors, and a
  dark theme that follows the system setting.
- Watched companies (`/api/v1/watched-companies`): watch a company through the public
  job board of its ATS (Greenhouse, Lever or Ashby), list them by name and stop watching
  one. Importing a watched company adds its open offers to the inbox as pending, skipping
  duplicates and discarding as expired the pending ones that left its board. It can be imported again at any time.
- Offers show the watched company they were imported from (`watched_company_id`,
  `watched_company_name`); offers of a company no longer watched stay in the inbox.
- Web app at `http://localhost:8081`, started by `just up` together with the API. It asks
  for the API token the first time, keeps it in the browser and asks again if the API
  rejects it.
- Inbox screen in the web app (`/inbox`): the pending, discarded and promoted offers,
  most recent first, each linking to its posting. Add an offer by hand (invalid fields
  and duplicates are shown in the form), import a public feed and
  see its summary (or when it can be imported again), discard an offer with an optional
  reason and undo it, restore discarded offers, and promote an offer to an application
  through a chosen channel.
- Searches screen in the web app (`/searches`): the search profiles, alphabetically.
  Create, edit (including clearing the optional fields) and delete a profile, with
  invalid fields and duplicate names shown in the form. Each profile opens its searches,
  grouped by job board, each one linking to the job board with its query, together with
  the work modes to set in each job board's own filter.
- Applications screen in the web app (`/applications`): the applications, most recent
  first, with their company, stage, outcome and channel, filtered by stage, outcome,
  channel or whether they are still active. Create an application for an existing
  company, optionally starting it as applied on a past date, with invalid fields shown
  in the form. Each application opens its detail with its history, where it can be
  edited (including clearing the optional fields) or deleted after confirming.
- Stage transitions on the application detail: move an application to a stage or close
  it with an outcome, optionally with a past date and a note, and undo its last transition
  after confirming. Transitions the funnel does not allow are shown with the API's message,
  and the history shows the note of each transition.
- Metrics screen in the web app (`/metrics`): the conversion from each stage to the next
  one, overall and for each channel with applications, and the applications in progress
  in each stage with their total. Each one comes as a table and a chart; a step no
  application reached shows its rate as "—", and with no applications the screen says so.
- Settings screen in the web app (`/settings`): the companies and the job boards,
  alphabetically, each in its own tab. Create, edit and delete them; invalid fields and
  duplicate names are shown in the form, and a company with applications says it cannot
  be deleted. Clearing the website of a company removes it.
- Watched companies screen in the web app (`/watched-companies`): the watched companies by
  name, with their ATS and board. Watch a company (invalid fields and duplicates are shown
  in the form), stop watching one after confirming, and import one for a search profile to
  see how many offers were found, matched, added, already in the inbox and expired. A board
  the ATS does not answer for says so.

### Changed

- **Breaking:** importing a feed or a watched company no longer takes a search profile
  (no request body): it adds every offer the source returns, skipping duplicates. The
  import summary reports how many of the added ones are `filtered` instead of `matching`.
  Himalayas is searched by the titles of every search profile.
- Metrics screen shows four key figures on top (active, interviewing, response rate and
  offers) and a rate bar next to each conversion rate.
- Lists are easier to scan: two-line rows with the company avatar (its logo in Settings),
  status chips with icons, relative dates ("today", "3d ago") with the full date on hover,
  and an icon and a short hint when a list is empty. Secondary row actions (discard, edit,
  delete, stop watching) appear on hover or keyboard focus, and are always visible on
  touch screens.
- Inbox and Settings tabs show how many items each one holds.
- Applications list shows each application's progress through the stages and its
  priority as bars.
- Application detail shows the history as a timeline, newest first, with an icon per
  stage, and icons next to each detail.
- Searches show keywords as tokens, with excluded ones in red.
- On narrow screens, lists hide their secondary columns.

### Fixed

- Every write is committed before the API answers. Before, the response could arrive
  first: a read right after a write could still return the old data, and a failed
  commit could still answer with a success.

## [0.2.0] - 2026-11-08

Phase 0, assisted discovery: offers arrive from search profiles, job boards and public
feeds into an inbox before becoming applications. Also corrections (edit, delete, undo)
and database backups.

### Added

- Public feeds (`/api/v1/feeds`): import into the inbox the offers of RemoteOK,
  Remotive, Himalayas and Jobicy that match a search profile
  (`POST /feeds/{feed}/imports`), skipping duplicates and discarding as `expired` the
  pending ones a feed no longer publishes. Each offer keeps the original link and its
  `feed`. Following each feed's terms, a feed can be imported once every 6 hours
  (`429 feed-cooldown` with `Retry-After`); a feed that does not answer returns
  `502 feed-unavailable` and changes nothing. `GET /feeds` shows the last and next import.

- Inbox (`/api/v1/offers`): add the offers found in the job boards (URL, company, title,
  optional job board and notes) and list them by status. The same company and title,
  ignoring case and extra spaces, is rejected as a duplicate even if it was discarded.
  Discard an offer with an optional reason (`POST /offers/{id}/discard`), restore it
  (`DELETE /offers/{id}/discard`), or promote it to an application in `evaluated`
  (`POST /offers/{id}/promotion`), which reuses or creates the company.
- A job board with offers cannot be deleted (`409 in-use`).

- `just seed-job-boards` registers the job boards of `backend/seeds/job_boards.json`
  (LinkedIn, Indeed, We Work Remotely, Jobicy, Welcome to the Jungle, Glassdoor and
  Himalayas) in the API run by `just up`, skipping the
  ones that already exist.

- Generated searches (`GET /api/v1/search-profiles/{id}/searches`): for every job board,
  the profile's search in that board's syntax and a URL ready to open. `boolean` joins
  titles with OR, keywords with AND and exclusions with NOT; `minus` uses -word for
  exclusions; `keywords` gets one search per title, without exclusions. The profile's
  work modes are listed so each board's own filter can be set.
- `minus` job board syntax (e.g. Indeed).

- Job boards (`/api/v1/job-boards`): create, view, list, edit and delete the job boards
  you search in, each with a search URL template (an http(s) URL with `{query}` and
  optionally `{location}`) and a search syntax (`boolean` or `keywords`).

- Search profiles (`/api/v1/search-profiles`): create, view, list, edit and delete what
  you look for, with job titles, required and excluded keywords, location and work modes
  (`remote`, `hybrid`, `onsite`). Names are unique ignoring case; texts are trimmed and
  repeated words kept once.

- Undo the latest transition of an application
  (`DELETE /api/v1/applications/{id}/transitions/latest`): it returns to its previous
  stage and outcome. The first stage cannot be undone.
- Delete an application created by mistake, with its history
  (`DELETE /api/v1/applications/{id}`).
- Edit a company (`PATCH /api/v1/companies/{id}`), keeping names unique, and delete one
  with no applications (`DELETE /api/v1/companies/{id}`; `409 in-use` otherwise).
- Applications show the current name of their company (`company_name`).
- `just db-backup` saves the database to `backups/`, and `just db-restore <file>` brings
  a backup back.

### Changed

- `just db-reset` and `just db-restore` ask for confirmation before touching data.

## [0.1.0] - 2026-11-08

First release: the MVP. The API tracks applications through the funnel and answers
where applications are lost and what is in progress.

### Added

- Funnel metrics: `GET /api/v1/metrics/conversion` (conversion from each stage to the
  next one), `GET /api/v1/metrics/conversion-by-channel` (the same, for each channel with
  applications) and `GET /api/v1/metrics/pipeline` (applications in progress per stage:
  no outcome and not accepted). An application counts as having reached its stage and
  every earlier one; rates are percentages with one decimal, or `null` with no data.
- Applications: create, edit, view and list them. An application belongs to a company
  and has a role and a channel (`portal`, `referral`, `recruiter_inbound`, `direct`,
  `networking`), plus an optional priority (`high`, `medium`, `low`), job posting URL and
  notes. It starts in `evaluated` (default) or `applied`, on today's date or a past one,
  and that first stage opens its history. Editing is partial (`PATCH`) and never changes
  the stage. The list is newest first, paginated, and filters by stage, outcome, channel
  and `active`.
- `unknown-company` error (422) when a request references a company that does not exist.
- Companies: create, view and list them. Names are required and unique ignoring case
  and surrounding spaces; the website is optional and must be an `http(s)` URL.
  The list is alphabetical (ignoring case) and paginated.
- Application stage transitions: move an application to any later stage, close it
  with an outcome allowed in its stage (`rejected`, `ghosted`, `withdrawn`,
  `offer_declined`), reactivate a `ghosted` application, and view its transition
  history. Transition dates default to today and cannot be in the future or before
  the previous transition.
- `GET /api/v1/applications/{id}` with the application's fields, its current stage and
  outcome, and its transition history.
- Paginated list responses share one envelope: `{items, total, limit, offset}`.
- Error contract: every error response is RFC 9457 problem details
  (`application/problem+json`) with a stable `type`; validation errors list each
  invalid field; unexpected errors return a generic 500 without internal details.
- Bearer token authentication for every `/api/v1` endpoint.
- `GET /health`, which also checks the database connection.
- `just up` runs the API and its database with Docker Compose (port 8080), migrating on start.
- Development setup: Justfile, Docker Compose Postgres, pre-commit, GitHub Actions CI,
  and a parallel test suite (unit, integration, BDD, migrations and API contract).

### Changed

- The backend runs on Python 3.14.
- CI only runs for backend-related changes and cancels superseded runs.

[Unreleased]: https://github.com/raullopeslopez/job_offer_funnel/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/raullopeslopez/job_offer_funnel/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/raullopeslopez/job_offer_funnel/releases/tag/v0.1.0
