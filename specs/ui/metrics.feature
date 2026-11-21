Feature: Metrics screen
  As a job seeker
  I want to see in one screen how my applications convert and what I have in progress
  So that I know where I lose applications and which channels work best without opening the API docs

  The screen has two views, "Offers" (the one it opens on) and "Funnel". "Offers" shows
  the offer quality of specs/inbox/offer_quality.feature: under "Offer quality", four
  cards (Precision, Losses, Flow and Real result) with the figure, a bar per week and a
  sentence, each a link to where the figure comes from; then "Why you discard", a bar per
  reason, and "By source", a table. A card without data shows "—", never 0%.
  "Funnel" shows the rules of specs/metrics/funnel_metrics.feature: each section has a
  table with the figures and a chart of the same figures. A rate is shown as a
  percentage with one decimal, and as "—" when no application reached the first stage of
  the step. The scenarios below without a view are on "Funnel".

  Background:
    Given I am signed in with a valid token

  Rule: "Offers" shows the offer quality of the last 4 weeks

    @component
    Scenario: The four key results, each linked to where it comes from
      Given the offer quality has a precision of 33.3% from 3 decided offers
      When I open the metrics
      Then the card "Precision" says "33.3%" and "1 promoted of 3 decided from Pending"
      And the card "Precision" links to the inbox

    # The card "Precision" is mine; under it, "With the AI's discards: {rate}" and "{n}
    # discarded by AI" when the triager discarded any.

    @component
    Scenario: The precision says apart the AI's discards
      Given the offer quality has a precision of 50.0% from 2 decided offers and 33.3% with 1 triager discard
      When I open the metrics
      Then the card "Precision" says "50.0%" and "1 promoted of 2 decided from Pending"
      And it says "With the AI's discards: 33.3%" and "1 discarded by AI"

    @component
    Scenario: A card without data shows a dash
      Given there is no offer quality yet
      When I open the metrics
      Then each card says "—"

    # "Changes to your criteria" lists the changes of specs/inbox/criteria_changes.feature,
    # the most recent first: what changed ("Excluded “Lead”") and what it did ("Today ·
    # took 6 out of Pending · lost 0 promoted"), each with "Undo".

    @component
    Scenario: Each change to the criteria with what it did, and undoing it
      Given the change "Excluded “Lead”" was made today and took 6 offers out of Pending
      When I open the metrics
      Then "Changes to your criteria" lists "Excluded “Lead”" with "Today · took 6 out of Pending · lost 0 promoted"
      And undoing it leaves "No changes yet."

    # Under "Why you discard", the suggestions of specs/inbox/criteria_suggestions.feature:
    # "Suggested: exclude “{word}” from {profile}", the line "In {k} of the {n}. Takes {m}
    # out of Pending, loses none you promoted." and "Not now" or "Exclude it" (a criteria
    # change). Nothing is applied until "Exclude it".

    @component
    Scenario Outline: A suggested exclusion, with "Not now" and "Exclude it"
      Given excluding "Lead" from "Backend" is suggested, in 2 of the 5 discarded, taking 3 offers out of Pending
      When I open the metrics and choose "<choice>"
      Then the app <does>
      And the suggestion is no longer shown

      Examples:
        | choice     | does                                                |
        | Not now    | does not suggest it again                           |
        | Exclude it | excludes "Lead" from "Backend", as a criteria change |

    @component
    Scenario: Discards by reason and the sources
      Given the offer quality has the discards "Stack" 2 and "Location" 1 and the source "Remote OK"
      When I open the metrics
      Then "Why you discard" lists "Stack", then "Location"
      And "By source" shows "Remote OK" with 5 imported, 3 that fit, 1 promoted and 1 discarded

    # "The AI triage" shows how the offer triager does (specs/inbox/offer_triages.feature),
    # once it has triaged an offer you decided on: its precision and its misses, each with
    # a bar per week, so that you see whether each batch does better. Once it has triaged a
    # near miss you reviewed (specs/inbox/near_miss_triages.feature), it also shows its
    # rescues and its lost rescues, the same way.

    @component
    Scenario: The triager's precision and misses
      Given the triager was right in 3 of 4 suggested discards decided and missed 1 of 4 triaged offers discarded
      When I open the metrics
      Then "The AI triage" says "75.0%" and "3 right of 4 suggested discards you decided"
      And it says "25.0%" and "1 missed of 4 triaged offers you discarded"

    @component
    Scenario: The triager's restores
      Given the triager discarded 4 offers and I restored 1
      When I open the metrics
      Then "The AI triage" says "25.0%" and "1 restored of 4 offers the AI discarded"

    @component
    Scenario: The triager's rescues and lost rescues
      Given the triager's OK near misses were rescued in 1 of 2 reviewed and 1 of 4 near misses rescued was marked KO
      When I open the metrics
      Then "The AI triage" says "50.0%" and "1 rescued of 2 OK near misses you reviewed"
      And it says "25.0%" and "1 marked KO of 4 near misses you rescued"

    @component
    Scenario: Without triaged offers decided there is no AI triage
      Given there is no offer quality yet
      When I open the metrics
      Then there is no "The AI triage"

  Rule: With applications, the screen shows their conversion and the active pipeline

    Background:
      Given a company named "Acme"
      And these applications for "Acme":
        | stage        | outcome   | channel  |
        | evaluated    |           | portal   |
        | evaluated    | withdrawn | portal   |
        | applied      |           | portal   |
        | applied      | ghosted   | portal   |
        | screening    | rejected  | referral |
        | interviewing |           | referral |
        | offer        |           | referral |
        | accepted     |           | referral |

    Scenario: The conversion from each stage to the next one
      When I open the metrics
      Then I see the conversion by stage:
        | from         | to           | reached_from | reached_to | rate  |
        | evaluated    | applied      | 8            | 6          | 75.0% |
        | applied      | screening    | 6            | 4          | 66.7% |
        | screening    | interviewing | 4            | 3          | 75.0% |
        | interviewing | offer        | 3            | 2          | 66.7% |
        | offer        | accepted     | 2            | 1          | 50.0% |

    Scenario: The conversion for each channel with applications
      When I open the metrics
      Then I see the channels, in order: "portal", "referral"
      And I see the conversion for channel "portal":
        | from         | to           | reached_from | reached_to | rate  |
        | evaluated    | applied      | 4            | 2          | 50.0% |
        | applied      | screening    | 2            | 0          | 0.0%  |
        | screening    | interviewing | 0            | 0          | —     |
        | interviewing | offer        | 0            | 0          | —     |
        | offer        | accepted     | 0            | 0          | —     |

    Scenario: The applications in progress in each stage
      When I open the metrics
      Then I see the active pipeline:
        | stage        | applications |
        | evaluated    | 1            |
        | applied      | 1            |
        | screening    | 0            |
        | interviewing | 1            |
        | offer        | 1            |
      And I see 4 active applications in total

  Rule: Without applications, the screen says so instead of showing empty figures

    Scenario: No applications yet
      When I open the metrics
      Then I see the message "No applications yet: add one to see your metrics"
