# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
While the version is `0.x`, the API may change without a major version bump.

## [Unreleased]

### Added

- Keyboard triage in the inbox: with the selected row focused, J or the down arrow selects the next offer, K or the up arrow the previous one, P promotes (near misses too) and D opens "Discard because", never discarding by itself. The keys are ignored while typing, and hints show them at the foot of the list and on the action bar buttons.
- A loading screen when the app opens: until the API answers for the first time (the
  pending count in the navigation), a loading animation covers the screen, which loads
  underneath. After 3 seconds it says the server is waking up (Render's free plan sleeps
  the API and Neon suspends the database), and if the request fails it offers to try
  again (`specs/ui/waking_up.feature`).
- Let the AI discard the offers it is sure of: `POST /offers/triager-discards` discards
  the pending offers that fit a profile and that the offer triager marked `ko` with
  `high` confidence, with the reason and word of its suggested discard, or `none`. It
  only happens when you ask for it ("Let AI discard {n}" in the inbox, with the count
  before you click, from the new `discardable` of `GET /offers/triager`), and "Undo"
  restores them all. Each such discard is marked as the AI's (`triager_discard`:
  `discarded`, or `restored` once you restore it, after which the AI never discards that
  offer again) and shows as "Discarded by AI" in the discarded view. It never counts as
  your decision: your precision, the triager's precision and misses, the discards by
  reason and by source, the criteria previews and suggestions, and what the triager is
  told all leave it out. The offer quality says it apart: `precision_with_triager`,
  `discarded_by_triager`, and how many of the AI's discards you restored
  (`triager_discards`, `restored_triager_discards`, `triager_restores`), shown under the
  Precision card and in "The AI triage".

- The offer reader tells the kind of role and the main stack: each reading now says
  whether the offer is an engineering job (`engineering`: building software, in a product
  team or with customers; not sales, pre-sales, customer support, consulting or product
  management, whatever the title says) and its main stack (`stack`: the languages and
  frameworks the role mainly works with), each with its evidence, like the other answers.
  An offer read as not an engineering job is filtered by the new rule `engineering`,
  whatever the profile, so a Forward Deployed Engineer doing pre-sales stays out and one
  writing code fits. A profile's excluded keywords now also exclude an offer whose main
  stack has one as a whole word ("Node" excludes "Node.js, TypeScript"; "Java" does not
  exclude "JavaScript"), with the stack's evidence in the `excluded` rule. The inbox strip
  gains a "Role" cell and a "Stack" cell that shows the stack read even when it filters
  nothing. Readings made before say neither, so they filter nothing new until read again.

- Near misses by rule in one request: `GET /offers/near-misses` gives the near misses
  grouped by the one rule they fail, in the order of the rules, each group with how many
  offers fail it and its most recent ones (`limit`, 1 to 100 per rule, 20 by default).
  The Filtered view's "One rule away" now loads with it, instead of one request per rule
  and another for the counts.
- Offer readings with Claude Code: with `OFFER_READER=claude-code` the offer reader is
  Claude Code on your Claude subscription (where `claude` is installed and signed in),
  like the offer triager, and `POST /offers/readings` reads up to 20 offers in a single
  request instead of 5; Groq stays the default. What it reads is kept and filters the same
  way. `just dev-prod` reads with it as well as triaging, and `just read-prod` reads every
  offer left to read through that API, so the reading queue no longer waits on Groq's
  quota.
- Published location as a filter: when the location an offer's source publishes is made
  only of known countries ("USA", "Canada, USA", "Germany / Netherlands") and none of them
  is a country the profile's location names, the offer's `location` rule fails for that
  profile, with the published location as its evidence, without waiting for the offer
  reader; such an offer is not read for that location. "Worldwide", "Anywhere", regions
  ("Europe", "EMEA") or any other text still leave it to the reading. As any filtered
  offer, it can be seen and rescued.
- Offer variants: every offer says its `base_title` (its title up to the first parenthesis,
  bracket, comma, or dash or vertical bar set off by a space) and its `variants`, how many
  pending offers that are not filtered share its company and base title, itself included.
  `GET /offers` takes `variants_together=true` to list the variants one after another,
  where the most recent of them would go; with `by_verdict`, only those within the same
  group of the verdict. The inbox lists Pending that way and shows the variants of a role
  as one closed group, "{company} · {base title} · {n} variants", that opens to show its
  offers: ten postings of one role per team no longer read as the same offer ten times.
- Pending by verdict: `GET /offers` takes `by_verdict=true` to list the offers OK first,
  then those with no verdict, then those KO by the reason of their suggested discard
  (title_word, stack, location, contract, company, and those with none last), each group
  from the most recently added. The inbox lists Pending that way and, once an offer has a
  verdict, groups it by verdict ("AI: OK", "Not triaged", "AI: KO · {reason}", "AI: KO")
  instead of by day, so the false positives can be discarded one after another.
- Offer search: `GET /offers` takes `matching_company_or_title`, only the offers whose
  company or title contains it, ignoring case and the spaces around it, and
  `job_board_id`, only the offers that came from that job board. Both combine with the
  other ways of listing the offers, and `total` counts only the offers they match.
- Offer triages with Claude Code: with `OFFER_TRIAGER=claude-code` the offer triager is
  the `claude` CLI on your Claude subscription (model `CLAUDE_CODE_MODEL`, `sonnet` by
  default) instead of Groq, 20 offers at a time instead of 5, told and answering the
  same, so its verdicts look the same in the app. It only runs where `claude` is
  installed and signed in; without it the triage is not available. `just dev-prod` runs
  the API that way on the production database (`PROD_DATABASE_URL`), to triage from your
  computer with `just frontend-dev`.
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

- The inbox on a phone (under 900 px): the list takes the whole width with the same rows
  and groups, and the AI controls sit under the views. Tapping a row opens the offer full
  screen, with Back, Original posting and its position ("3 of 7"), and its actions at the
  foot as 50 px buttons; "Discard because" shows full-width rows that say what each one
  refers to (country, company). After an action the screen goes back to the list, with the
  message and Undo. Nothing is open until you tap a row.
- Filtered, in the list column beside the reading pane: the groups of "One rule away" are
  always open (no more "Show" and "Hide"), so every near miss is a row you can choose,
  and the first of them opens in the pane. "No title of yours" names its profile:
  "No title of yours · {n} offers · {profile}" (`specs/ui/inbox.feature`).

- The inbox is a list of rows and a reading pane, with no cards: each offer is one row
  (its title, company, where it is, its age and its source), and choosing a row opens
  the offer in the pane, with its rules, its AI verdict and its actions. The first offer
  of the view opens on its own, and the selected row is marked. On a wide screen the
  list is a column next to the pane; on a phone the pane follows the list. The groups
  stay the same (by verdict or by day, and "Maybe" at the end of Pending); the variants
  of a role are one row that says "+{n} variants", and its pane opens them in the list
  (`specs/ui/inbox.feature`).
- The AI controls of Pending are in the list header, as discreet buttons and plain text
  with no banner: "Triage with AI" with its result in one line, "Let AI discard {n}"
  with its sentence, and the triager's criteria suggestion, one at a time, as a block
  between two lines (the change, why, its effect in green, "Exclude it" and "Not now";
  `specs/ui/inbox.feature`).
- Each inbox row says in one line what decides its offer, with a text label and the
  company's mark: "AI: OK · High" or "AI: KO · Medium" with the why of its side; "Not
  triaged" with what its reading says (mode, location, contract, stack) or "Nothing to
  read: email alert"; "Near miss" or "Filtered" with the rule that filtered it ("Mode:
  Hybrid, you ask Remote"); "Discarded" or "Discarded by AI" with the reason; "Promoted"
  with "Application created" (`specs/ui/inbox.feature`).
- The reading pane of the inbox reads like a page: the company with its mark, the source
  and the age, "Original posting" as a link and the title big, with its status line
  ("Near miss · filtered by one rule", "Discarded by AI · Contract"). The AI verdict is set
  off by a line, with no box, and its quotes are always visible under "Why yes" and "Why
  not" (no more "View evidence"); an OK near miss says "worth rescuing". The rules are a
  list, a line per rule, with a filled dot when it passes, a hollow one when it is "Not
  stated" and a red one with "filtered it" when it filtered the offer, and the literal
  evidence under that rule.
- The actions of an offer in the inbox are a bar fixed at the foot of the reading pane,
  with a line above and no box, and it says which offer of the view is open ("3 of 7").
  "Discard" opens its reasons in the bar itself. With a suggested discard, "Discard:
  {reason}" is the main action, "Promote" is secondary and "Other reason" opens the rest
  of the reasons; it is still my click. After promoting, discarding, restoring or marking
  an offer the next offer of the view opens, or the previous one when it was the last
  (`specs/ui/inbox.feature`). A promoted offer says "Open application".
- An offer is not a stable job when it is freelance or paid by the hour or by the task,
  even if it says full-time: the offer reader is told so.
- Inbox on a phone: the title of an offer stays readable while discarding it, its words
  show under "A word in the title" and choosing one discards (or, with a profile, proposes
  excluding it) in one tap; the other reasons are full-width rows that say what they refer
  to (its country, its company). The actions go full width at the foot of each offer, the
  rule strip shows two rules to a row without cutting their values, and an offer with many
  countries shows the first one and how many more ("Spain +27 countries").

- Excluded keywords only filter an offer when they are in its title as a whole word or
  its plural in "s" or "es": "Lead" filters "Lead Engineer", "Engineer (Tech-Lead)" and
  "Engineer for Leads", but no longer "Leading" nor "Mislead". Titles and keywords still
  match inside longer words. Filter reasons, near misses, criteria previews and
  suggestions follow the same rule.

- Offer triages: each triaged offer now says what speaks for it and what against it, and
  how sure the triager is. `triage.why` is replaced by `why_yes` and `why_not` (each
  `{why, quote}`, or null when there is nothing to say on that side; the quote is kept
  only if it is in the title or the description letter for letter) and `confidence`
  (`low`, `medium`, `high`, or null). Offers triaged before keep their why on the side of
  their verdict, with no quote and no confidence. The triager now judges the work an offer
  describes (its stack, platform and duties) against the profiles, so an offer whose title
  passes the filters but whose job is of a kind the profiles exclude (mobile, frontend…)
  is marked KO; its why names what in the offer decides it. In the inbox, each triaged
  offer has an AI section under its strip with its verdict, confidence, why yes and why
  not, and the suggested discard as "Discard: {reason}".
- Offer readings: the offer reader is also given the offer's title and the location its
  source publishes, and an answer's evidence may be quoted from any of them, not only
  from the description. A remote job whose title or location names a place
  ("Backend Engineer - UK", "US Remote", "USA only") is read as one that can only be done
  living there, unless its description opens it to other places, so it is filtered for
  a profile whose location that place excludes.
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

- The triager no longer marks near misses OK just for the role: it judges the rule that
  filtered them, and is told each offer's published location and each profile's location.
  A near miss is OK (to rescue) only when its why yes quotes, letter for letter, a sentence
  of at least four words of its description that rebuts that rule (for the location rule,
  one saying it can be done from the profile's location); a quote of its title or its
  published location does not count. Otherwise it is kept as KO, rightly filtered, and
  suggests no rule to relax.
- Discarding in the inbox shows at once: the offer leaves the list and "Offer discarded"
  (with Undo) appears as soon as the discard is done, instead of after the inbox lists
  its offers again, which could take half a minute. "Discard: {reason}" no longer keeps
  spinning meanwhile, and "Cancel" is disabled while the discard is being done.
  Restoring, promoting and marking as rightly filtered also say so without that wait.
- Listing the pending offers that are near misses, or that fail a rule, no longer fails
  when there are tens of thousands of them.
- Faster inbox reads: listing and counting offers no longer waits about two seconds on
  every request while the database compiles the filter (Postgres JIT, now turned off for
  the API's connections, on any Postgres it runs against).
- Inbox on a phone: the page no longer grows wider than the screen (the status tabs
  scroll inside their pill), so the browser does not zoom it out; and in dark mode the
  form fields, such as "Job board" in "Import job board", are dark instead of white. The
  buttons at the top wrap to a new row instead of breaking their labels.

- Offer countries: "Anywhere in France, Belgium, Spain" shows France, Belgium and Spain,
  no longer "Worldwide" too; only "Anywhere" alone or "Anywhere in the world" means any
  country.
- Offers imported before locations were kept get one: when a job board, a watched company
  or a job alert publishes again an offer that is already in the inbox and has no
  location, whatever its status, the offer keeps the location published now (an offer
  with a location keeps its own). It still counts as already in the inbox. A pending offer
  that gets its location loses its readings and is read again with it; one that is no
  longer pending keeps them.
- The offers of an Ashby board keep their secondary locations after their location
  ("United Kingdom, Spain, Dublin"), so a job also open in Spain is no longer read as
  only for the United Kingdom.

- Feed imports: an offer whose feed publishes the title or the company with HTML
  character references ("&#038;" or "&amp;" for "&", as Jobicy does) now keeps the
  characters they stand for, so "Quest Defense Systems &#038; Solutions" is "Quest Defense
  Systems & Solutions" and its title matches the words of the search profiles. The offers
  already imported are fixed too.
- An offer with the same URL as one already in the inbox (ignoring a trailing slash and
  `utm_*` parameters) is now the same offer, even with another company or title: adding
  it answers `409 already-exists`, and imports skip it as already in the inbox. Before, a
  company that edited a title on its board (seen on Ashby) got its offer imported twice.
  Copies imported before stay until discarded by hand.
- Importing a job board or a watched company no longer fails with a 500 when only some
  of its new offers have a location.
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
