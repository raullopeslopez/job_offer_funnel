# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
While the version is `0.x`, the API may change without a major version bump.

## [Unreleased]

### Added

- Offer countries: every offer has `location`, where the job is as its source publishes
  it (Remote OK, Remotive, Himalayas, Jobicy, Greenhouse, Lever, Ashby and LinkedIn job
  alerts; null for offers added by hand, RSS items and offers imported before), and
  `countries`, the known countries it names in order (by English name, or USA, US, UK and
  UAE in capitals), with `Worldwide` for jobs that can be done from any country. The
  inbox shows a tag per country, or the location as published when it names none.
- Offer triages: `POST /api/v1/offers/triages` has a language model (the offer triager,
  on Groq with `GROQ_API_KEY`) compare up to 5 pending imported offers that fit a profile,
  description included, with your last promoted and discarded offers and with its own
  mistakes (suggestions you rejected by promoting, offers it marked OK that you
  discarded). It marks each offer `ok` or `ko` (a false positive: it passed your filters
  but you would discard it), with why in one sentence. A `ko` may suggest a discard with a
  reason of the list and its evidence (a word of the title, or a sentence of the
  description letter for letter); nothing is discarded on its own. It may also suggest
  excluding a word from a profile, from the `ko` offers that have it: the suggestion joins
  the criteria suggestions only if it would have filtered no offer you promoted and at
  least one you discarded. Each offer is triaged once; it answers
  `{triaged, ok, ko, failed, left}`. `GET /api/v1/offers/triager` says
  whether it is available; without it the triage answers 503 `offer-triager-unavailable`.
- Near miss triages: the triage also takes the near misses (filtered by a single rule, not
  by the title), after the offers that fit, telling the triager the rule that filtered
  each. For a near miss, `ok` is a false negative (counted in `to_rescue`) and `ko` means
  rightly filtered; it stays filtered either way. An `ok` near miss may suggest relaxing
  the rule that filtered it: stop excluding the word, stop asking for the keyword it lacks
  (a profile asks for all of them), or accept its work mode. It is kept only if no offer
  you discarded would fit with the change.
- Criteria suggestions have `rule`, `word` and `after` (the rule's value with the
  change), instead of `excluded_keywords`; "Not now" takes the `rule` too (by default
  `excluded_keywords`). Criteria previews say `discarded_fitting`: the discarded offers
  the change would make fit.
- Offer quality: the triager's rescues (the OK near misses you rescued, of those you
  reviewed) and lost rescues (the near misses you rescued that it marked KO).
- Metrics: "The AI triage" also shows the triager's rescues and lost rescues, with a bar
  per week, once it has triaged a near miss you reviewed.
- Inbox: the triage says how many near misses are "to rescue"; a near miss with a verdict
  shows it, and with a suggestion "Improve the filter" with what it would bring into
  Pending and "Relax it", a criteria change made from that offer.
- Offers have `triage` (`{verdict, why}` or null) and `suggested_discard`
  (`{reason, evidence}` or null).
- Offer quality: the triager's precision (suggested discards you discarded of those you
  decided) and misses (offers it marked OK that you discarded), in total and
  week by week.
- Inbox: "Triage with AI" in Pending triages batch after batch, saying how many are OK and
  KO. Each triaged offer says "AI: OK" or "AI: KO" and why; with a suggested discard, it adds
  the reason and its evidence and "Discard as suggested". A KO offer the triager's
  suggestion comes from offers "Improve the filter" with what excluding the word would do
  and "Exclude it", a criteria change made from that offer; the suggestion also shows above
  the offers with "Not now" and "Exclude it". Metrics:
  "The AI triage" with the triager's precision and misses.
- Frequent titles: `GET /api/v1/offers/frequent-titles?search_profile_id=` lists the
  titles of at least 2 filtered offers with none of the profile's titles (grouped
  ignoring case and spaces, up to 5, the most frequent first), with how many have the
  profile's keywords, how many pass its reading and what adding the title would do.
- Inbox: Filtered shows "No title of yours" with the most frequent titles and "Add title",
  a logged criteria change.
- Criteria suggestions: `GET /api/v1/criteria-suggestions` suggests excluding a word from a
  search profile when it is in the titles of at least 3 discarded offers and of no
  promoted one, with the offers behind it and what excluding it would do; only counting,
  no language model. The offer triager's suggestions join them, with `source: triager`,
  its `why` and the offers they come from. `POST /api/v1/criteria-suggestions/dismissals` ("Not now") hides one
  for good. Nothing is applied on its own.
- Metrics: the suggestions show under "Why you discard", with "Not now" and "Exclude it".
- Criteria changes: `POST /api/v1/criteria-changes` changes one rule of a search profile
  (and only one: `validation-error` otherwise) and logs it with the rule before and after,
  what it did when applied (the counts of a preview) and, with `offer_id`, the offer it
  came from. `GET /api/v1/criteria-changes` lists them from the most recent;
  `DELETE /api/v1/criteria-changes/{change_id}` undoes one, putting the rule back
  (`rule-changed-since` if a later change edited the same rule). Editing a profile
  directly is not logged.
- Metrics: "Changes to your criteria" lists each change with what it did, and "Undo".
  "Discard and exclude" in the inbox is logged as a change from that offer.
- Offer quality: `GET /api/v1/offers/quality` measures the offers added in the last 4
  weeks, in total and week by week: precision (promoted ÷ decided from Pending, without
  rescues and expired offers), losses (near misses rescued ÷ reviewed, and how many are
  left to review), flow (offers that fit the profiles now, and the weekly average), real
  result (of the promoted, the applications that reached `applied` and `screening`), the
  discards by reason and what each source brought.
- Metrics: the screen opens on "Offers", the offer quality: four cards linked to where
  each figure comes from, "Why you discard" and "By source". The previous figures are
  under "Funnel".
- Criteria previews: `POST /api/v1/offers/criteria-previews` takes a search profile and the
  same changes as editing it, saves nothing, and says how many pending offers would come
  into Pending (`entering_pending`) and leave it (`leaving_pending`), and how many promoted
  and discarded offers the change would have filtered (`promoted_filtered`,
  `discarded_filtered`; expired offers do not count).
- Inbox: discarding an imported offer because of "A word in the title" proposes excluding
  the word from its profile, with what the change would do, and "Only discard this one" or
  "Discard and exclude" it.
- Rescues and rightly filtered offers: promoting a filtered offer records it as a rescue
  (`review: rescued`) with the rules that filtered it then (`review_rules`).
  `POST /api/v1/offers/{offer_id}/rightly-filtered` marks a filtered offer as reviewed
  (`review: rightly_filtered`): it stays filtered but is no longer a near miss
  (`offer-not-filtered` if it is not filtered); `DELETE` on the same path undoes it.
  `GET /api/v1/offers/filtered-counts` also counts the near misses ever reviewed
  (`reviewed_near_misses`) and those rescued (`rescued_near_misses`).
- Inbox: "Rightly filtered" next to "Promote anyway" in "Maybe" and in the groups of the
  filtered view takes the offer out of the group, with "Undo" in the notice.
- Inbox: every imported offer shows its five rules (Title, Keywords, Mode, Location,
  Contract) with the value that passed each one, "Not stated" when unknown, "Any" when the
  profile does not ask for it, or the value against what the profile asks and the sentence
  of the description behind it when the rule filtered the offer. The pending view ends
  with "Maybe", the three most recent near misses, to promote anyway. The filtered view
  groups the near misses by the rule that filtered them ("One rule away", with how many
  fail it for each word or value) and lists the rest as "Further away".
- Filter reasons: every pending imported offer has a `filter_reason` with the result of
  each rule (`title`, `keywords`, `excluded`, `work_mode`, `location`, `stable`: `passed`,
  `unknown` or `failed`) against its reference profile, the one whose rules it fails the
  fewest times, with what explains it: the words found and missing, or the value read and
  its evidence. It also says whether the offer has a description, and whether it is a
  `near_miss` (filtered, its title passes and it fails a single rule). The offers can be
  listed by `near_miss` and by `failed_rule`, and `GET /api/v1/offers/filtered-counts`
  counts the filtered offers, the near misses and the offers failing each rule.
- Offer readings: `POST /api/v1/offers/readings` has an offer reader (a language model)
  read the description of up to 5 pending imported offers that fit a search profile by
  its words, and answers how many it read, failed on and left. A reading says the offer's
  work mode, whether the job can be done living in the profile's `location`, and whether
  it is a stable job (full-time with no end date, as an employee or a contractor), each
  with the sentence of the description that says so; an answer without that sentence in
  the description is not kept. Offers show their `readings`, and what a reading says
  filters the offer: a work mode the profile does not accept, a job that cannot be done
  from its location, or one paid by the task or the hour, temporary or part-time. What
  the description does not say never filters. Needs `GROQ_API_KEY`; without it nothing is
  read (`offer-reader-unavailable`) and everything else works the same. The scheduled
  import reads the new offers after importing, a few a minute.

- LinkedIn job alerts: a job board can be imported from its job alert emails
  (`import_method: email` with `email_alert: linkedin`; at most one job board per alert,
  `email-alert-taken` otherwise), also from the settings screen. `POST
  /api/v1/email-alerts/imports` takes an alert email (sender and plain-text body) and
  adds its offers to that job board like an import: pending, filtered when they fit no
  search profile, duplicates skipped, links without the email's tracking. Every LinkedIn
  job alert is read, whatever its search. Other emails are rejected (`unsupported-alert`),
  and so are alerts no job board imports (`email-alert-not-imported`). Such job boards are
  not imported on demand (`job-board-imported-by-email`). The scheduled import reads new
  alerts by IMAP from the Gmail account dedicated to them when `GMAIL_ADDRESS` and
  `GMAIL_APP_PASSWORD` are set, and labels each one `funnel-imported`.

- Job boards can be imported from their RSS: `import_method: rss` with an
  `rss_url_template` (an http(s) URL with `{query}`). The RSS is read once per title of
  the search profiles, and each item reading `Company: Title` becomes an offer, with the
  same 6-hour limit and expiry as the feeds. Evenbreak is the first one: `just
  seed-job-boards` registers it as imported, and an existing Evenbreak job board switches
  to its RSS on upgrade. The settings screen sets the RSS of a job board.

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

- Job boards say how their offers reach the inbox: `import_method` is `none` (by hand, with
  the generated searches) or `api`, with the public `feed` they are imported from (`remoteok`,
  `remotive`, `himalayas` or `jobicy`; one job board per feed). Import one with
  `POST /api/v1/job-boards/{id}/imports`; each job board shows `last_imported_at` and
  `next_import_at`. The settings screen sets the feed of a job board, and
  `just seed-job-boards` registers Remote OK, Remotive, Himalayas and Jobicy as imported.

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

- Profiles screen: each profile shows what makes an offer fit (by words: job titles,
  keywords and excluded words; by the description: where you live and the work modes) and
  its generated searches, with each job board's syntax and an "Open search" button. The
  first profile starts open; the others open with "Show fit and searches". The searches no
  longer open in a dialog.
- Discard reasons: the reason of a discard is now one of a closed list (`title_word`,
  `stack`, `location`, `contract`, `company`, `none`, plus `expired`, set only by the
  imports), and `none` when none is given. With `title_word`, `word` says the word of the
  title that does not fit (`discard_word` in the offer); a word the title does not have is
  rejected (`word-not-in-title`). The free-text reasons already saved became `none`, their
  text kept at the end of the offer's notes. Breaking in `/v1`: `reason` no longer takes
  free text.
- Inbox: "Discard" opens the offer itself instead of a dialog. The words of its title
  become buttons and, after "Discard because", one click on a reason discards it ("A word
  in the title" once a word is marked). The discarded offers show their reason.
- Web app: a new "ink and signal" look in light mode. Ink and neutrals for the interface,
  Geist for every heading, pill-shaped buttons with 44px touch targets and thin borders
  instead of shadows. The dark mode keeps its current colors for now.
- Web app: the menu has six screens in two groups. "Offers": Inbox, with the number of
  pending offers, Profiles (formerly Searches) and Sources (the job boards, with the
  watched companies below them). "Pipeline": Applications, Metrics and Companies (the
  companies formerly in Settings). The app opens on the inbox; Home, Settings and Watched
  companies are gone (`/searches`, `/settings` and `/watched-companies` no longer exist).
- Web app: the inbox shows each offer as a piece instead of a table row, grouped by the
  day it was added (Today, Yesterday, Earlier). Every piece shows its source, company and
  age, and a strip with what its description says of the mode, the location and the
  contract ("Not stated" when it does not say). The heading counts the offers to decide,
  "Show more" loads the next ones, and a promoted offer links to its application.
- Web app: the sources are grouped in five blocks by how offers reach the inbox: API
  import, Watched companies, RSS import, Email alerts and Added by hand, with a generated
  search. Each block says what the app does and what you do. Job boards imported by API
  or RSS have "Import now", and those added by hand link to their searches in Profiles.
- **Breaking:** importing a feed or a watched company no longer takes a search profile
  (no request body): it adds every offer the source returns, skipping duplicates. The
  import summary reports how many of the added ones are `filtered` instead of `matching`.
  Himalayas is searched by the titles of every search profile.
- **Breaking:** feeds are imported through their job board. `GET /api/v1/feeds` and
  `POST /api/v1/feeds/{feed}/imports` are gone (use the job boards and
  `POST /api/v1/job-boards/{id}/imports`), offers no longer have `feed` (an imported offer
  has the `job_board_id` and `job_board_name` of its job board), and the import summary
  has `job_board_id` instead of `feed`. Existing offers and import dates move to the job
  boards named Remote OK, Remotive, Himalayas and Jobicy, created if missing.
- A search profile's generated searches leave out the job boards that are imported.
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

- Scheduled imports no longer fail the whole run when a feed, RSS or ATS board is down
  (`feed-unavailable`, `board-unavailable`): it is skipped and tried again in the next run.
- Importing Jobicy no longer loses most of its offers nor discards open ones: its feed
  only publishes its latest offers (a few hours of postings), so an import now reads up
  to 300 of them instead of 50, and its pending offers are no longer discarded as
  `expired` when they leave the feed.
- Every write is committed before the API answers. Before, the response could arrive
  first: a read right after a write could still return the old data, and a failed
  commit could still answer with a success.
- Offer readings filter fewer good offers. A job is read as hybrid or onsite only when it
  requires days at an office: an optional office, remote as one of the options or
  occasional travel are remote. A job is read as not doable from the profile's `location`
  only when it requires living, being a citizen or having the right to work somewhere
  else: preferred locations, working hours, languages, the salary's currency and where
  the company or its team are no longer count. Offers already read keep their reading.

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
