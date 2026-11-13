Feature: Inbox screen
  As a job seeker
  I want to review the offers I collect from the job boards in one screen
  So that I triage each one without opening the API docs

  The rules of the offers (duplicates, statuses, promoting, import limits) are those
  of specs/inbox/inbox.feature and specs/inbox/job_board_imports.feature. This screen
  only shows them: every rejection appears as a message, next to its field when
  it belongs to one. The inbox opens with the pending offers that are not filtered,
  most recent first; the filtered ones (specs/inbox/filtered_offers.feature) have
  their own view.

  Every offer is a piece with the same parts, wherever it came from: its source,
  company and age, its title, its actions and a strip of rules. The pieces are
  grouped by the day they were added: Today, Yesterday and Earlier.

  An imported pending offer has a filter reason (specs/inbox/filter_reasons.feature),
  and its strip has five cells, one per rule of its reference profile: Title,
  Keywords, Mode, Location and Contract. The Title cell also holds the excluded
  keywords. Each cell says the value that passed the rule, "Not stated" when it is
  unknown, or, when the rule filtered the offer, the value against what the profile
  asks, marked "filtered it". A cell whose rule the profile does not ask for says
  "Any". Only filtered offers have a failed cell, so it only shows in "Maybe" and in
  the filtered view. Without a description to read, Mode, Location and Contract merge
  into one cell that says why. Offers with no filter reason (added by hand, discarded
  or promoted) keep the strip of what their reading says of the mode, the location
  and the contract (specs/inbox/offer_readings.feature).

  The near misses (a filtered offer whose title passes and that fails exactly one rule)
  are the filtered offers worth a second look: the last group of the pending view,
  "Maybe", shows the three most recent, and the filtered view groups them all by the
  rule that filtered them.

  Background:
    Given I am signed in with a valid token

  # --- Viewing ---

  Scenario: The inbox shows the pending offers, most recent first
    Given offers for "Acme" as "A", "B" and "C", added in that order
    And an offer for "Acme" as "Discarded one" that was discarded
    When I open the inbox
    Then I see the offers, in order: "C", "B", "A"
    And the inbox says "3 to decide"

  Scenario Outline: Show the offers of another status
    Given an offer for "Acme" as "Pending one"
    And an offer for "Acme" as "Discarded one" that was discarded
    And an offer for "Acme" as "Promoted one" that was promoted
    When I open the inbox showing the "<status>" offers
    Then I see the offers, in order: "<title>"
    And the inbox says "<heading>"

    Examples:
      | status    | title         | heading     |
      | pending   | Pending one   | 1 to decide |
      | discarded | Discarded one | 1 discarded |
      | promoted  | Promoted one  | 1 promoted  |

  # @component: the E2E tests add every offer today; a component test dates them.

  @component
  Scenario: The offers are grouped by the day they were added
    Given an offer for "Acme" as "New one" added today
    And an offer for "Acme" as "Recent one" added yesterday
    And an offer for "Acme" as "Old one" added a week ago
    When I open the inbox
    Then I see the groups, in order: "Today", "Yesterday", "Earlier"

  Scenario: More offers are shown on demand
    Given 21 offers for "Acme"
    And I am on the inbox
    When I ask to see more offers
    Then I see 21 offers listed

  # --- The strip of rules ---

  Scenario: An offer added by hand says it has nothing to read
    Given an offer for "Acme" as "Backend Engineer"
    When I open the inbox
    Then the offer "Backend Engineer" shows "Mode, location and contract unknown: you added it by hand"

  # @component: only an import gives an offer a filter reason, only the external reader
  # makes readings, and the E2E tests cannot reach the feeds nor the reader.

  @component
  Scenario: An offer without a filter reason shows what its reading says
    Given an offer for "Acme" as "Backend Engineer" that was discarded
    And its reading says the mode is "hybrid", the location "Spain" is admitted and the contract is stable
    When I open the inbox showing the "discarded" offers
    Then the offer "Backend Engineer" shows the cells:
      | rule     | state | value    |
      | Mode     | pass  | Hybrid   |
      | Location | pass  | Spain    |
      | Contract | pass  | Stable   |

  @component
  Scenario Outline: Each cell of an imported offer says the value that passed its rule
    Given a search profile named "Backend" with:
      | titles     | Backend Engineer |
      | keywords   | Python, Django   |
      | location   | Spain            |
      | work_modes | remote           |
    And an imported offer for "Acme" as "Backend Engineer" whose filter reason gives "<rule>" as "<result>" with "<value>"
    When I open the inbox
    Then the offer "Backend Engineer" shows "<shown>" in its "<cell>" cell, as "<state>"

    Examples:
      | rule      | result  | value            | cell     | shown            | state   |
      | title     | passed  | Backend Engineer | Title    | Backend Engineer | pass    |
      | keywords  | passed  | Python, Django   | Keywords | Python, Django   | pass    |
      | work_mode | passed  | remote           | Mode     | Remote           | pass    |
      | work_mode | unknown |                  | Mode     | Not stated       | unknown |
      | location  | passed  | yes              | Location | Spain            | pass    |
      | stable    | passed  | yes              | Contract | Stable           | pass    |
      | stable    | unknown |                  | Contract | Not stated       | unknown |

  @component
  Scenario: A rule the profile does not ask for says "Any"
    Given a search profile named "Backend" with the title "Backend Engineer"
    And an imported offer for "Acme" as "Backend Engineer" that fits it
    When I open the inbox
    Then the offer "Backend Engineer" shows "Any" in its "Keywords", "Mode" and "Location" cells

  @component
  Scenario Outline: An offer with no description to read merges the rules of its reading
    Given a search profile named "Backend" with the title "Backend Engineer"
    And an offer for "Acme" as "Backend Engineer" imported through <method>, without a description
    When I open the inbox
    Then the offer "Backend Engineer" shows "Backend Engineer" in its "Title" cell
    And the offer "Backend Engineer" shows "<merged>"

    Examples:
      | method   | merged                                                                                  |
      | an email | Mode, location and contract unknown: email alerts arrive without a description to read |
      | a feed   | Mode, location and contract unknown: the offer has no description to read              |

  # --- Filtered offers ---
  # @component: only an import makes filtered offers.

  @component
  Scenario Outline: A failed cell says the value against what the profile asks
    Given a search profile named "Backend" with:
      | titles            | Backend Engineer |
      | keywords          | Python, Django   |
      | excluded_keywords | Senior           |
      | location          | Spain            |
      | work_modes        | remote           |
    And a filtered offer for "Acme" as "<title>" that fails "<rule>" with "<value>" and the evidence "<evidence>"
    When I open the inbox showing the "filtered" offers
    Then the offer "<title>" shows "<shown>" in its "<cell>" cell, marked "filtered it"
    And the offer "<title>" shows the evidence "<evidence>"

    Examples:
      | title                   | rule      | value  | evidence                 | cell     | shown                    |
      | Senior Backend Engineer | excluded  | Senior |                          | Title    | "Senior", you exclude it |
      | Backend Engineer        | keywords  | Django |                          | Keywords | Missing: Django          |
      | Backend Engineer        | work_mode | hybrid | Two days in the office   | Mode     | Hybrid, you ask Remote   |
      | Backend Engineer        | location  | no     | Only residents of the US | Location | Not from Spain           |
      | Backend Engineer        | stable    | no     | A six-month contract     | Contract | Not stable               |
      | Data Engineer           | title     |        |                          | Title    | No title of yours        |

  @component
  Scenario: The pending view leaves out the filtered offers
    Given a search profile named "Backend" with the title "Backend Engineer"
    And the job board "Remote OK" was imported with an offer for "Acme" as "Backend Engineer"
    And the job board "Remote OK" was imported with an offer for "Globex" as "Data Engineer"
    When I open the inbox
    Then I see the offers, in order: "Backend Engineer"

  @component
  Scenario: "Maybe" closes the pending view with the three most recent near misses
    Given 5 near misses and a filtered offer that fails two rules
    When I open the inbox
    Then the last group is "Maybe · 3 of 5 near misses"
    And it says "Filtered by a single rule. Promoting one tells the app the rule was too strict."
    And it shows the three most recent near misses, each with its failed cell and "Promote anyway"

  @component
  Scenario: Without near misses there is no "Maybe"
    Given a filtered offer that fails two rules
    When I open the inbox
    Then there is no "Maybe" group

  @component
  Scenario: Promote a near miss anyway
    Given a near miss for "Acme" as "Backend Engineer"
    And I am on the inbox
    When I promote anyway the near miss "Backend Engineer" through "portal"
    Then I see the message "Application created"

  @component
  Scenario: The filtered view groups the near misses by the rule that filtered them
    Given the near misses:
      | title                   | rule      | value  |
      | Junior Backend Engineer | excluded  | Junior |
      | Junior Python Developer | excluded  | Junior |
      | Backend Intern          | excluded  | Intern |
      | Backend Engineer        | work_mode | hybrid |
    And a filtered offer that fails two rules
    When I open the inbox showing the "filtered" offers
    Then I see "One rule away · 4 offers"
    And I see the groups, in order:
      | group              | count | breakdown           |
      | A word you exclude | 3     | Junior 2 · Intern 1 |
      | Mode               | 1     | Hybrid 1            |
    And I see "Further away · 1 offer"

  @component
  Scenario: A group of near misses opens to show its offers
    Given the near misses:
      | title                   | rule     | value  |
      | Junior Backend Engineer | excluded | Junior |
    And I am on the inbox showing the "filtered" offers
    When I show the group "A word you exclude"
    Then the group lists "Junior Backend Engineer" with its source, its company, its failed cell and "Promote anyway"

  @component
  Scenario: The offers further away are listed with their strip
    Given a filtered offer for "Globex" as "Data Engineer" that fails the title
    And a near miss for "Acme" as "Junior Backend Engineer"
    When I open the inbox showing the "filtered" offers
    Then the block "Further away" lists the offers, in order: "Data Engineer"
    And the offer "Data Engineer" shows "No title of yours" in its "Title" cell, marked "filtered it"

  Scenario: An empty inbox says so
    When I open the inbox
    Then I see that there are no offers

  Scenario: Each offer opens its original posting
    Given an offer for "Acme" as "Backend Engineer" with URL "https://jobs.example/1"
    When I open the inbox
    Then the offer "Backend Engineer" links to "https://jobs.example/1"

  # --- Adding by hand ---

  Scenario: Add an offer by hand
    Given a job board named "LinkedIn"
    And I am on the inbox
    When I add an offer with:
      | url       | https://jobs.example/1       |
      | company   | Acme                         |
      | title     | Backend Engineer             |
      | job_board | LinkedIn                     |
      | notes     | Found through a saved search |
    Then I see the offers, in order: "Backend Engineer"
    And the offer "Backend Engineer" shows "Acme" and "LinkedIn"

  Scenario: An invalid URL is shown next to its field
    Given I am on the inbox
    When I add an offer for "Acme" as "Backend Engineer" with URL "not-a-url"
    Then I see an error on the field "url"
    And the offer is not added

  Scenario: A duplicate offer is rejected with a message
    Given an offer for "Acme" as "Backend Engineer"
    And I am on the inbox
    When I add an offer for "ACME" as "backend engineer"
    Then I see the message "The offer already exists"
    And the inbox says "1 to decide"

  # --- Importing job boards ---
  # @component: the E2E tests cannot reach the public feeds; component tests cover these.

  @component
  Scenario: Import a job board
    Given a search profile named "Backend" with the title "Backend Engineer"
    And a job board named "Remote OK" imported from the feed "remoteok"
    And the feed "remoteok" publishes an offer for "Acme" as "Backend Engineer"
    And I am on the inbox
    When I import the job board "Remote OK"
    Then I see the import summary: 1 found, 1 added, 0 filtered, 0 already in the inbox
    And I see the offers, in order: "Backend Engineer"

  @component
  Scenario: A job board imported too recently says when it can be imported again
    Given the job board "Remote OK" was imported 1 hour ago
    And I am on the inbox
    When I import the job board "Remote OK"
    Then I see that the job board "Remote OK" can be imported again in 5 hours

  Scenario: Only the job boards imported from a feed or an RSS can be imported
    Given a job board named "Indeed"
    And a job board named "LinkedIn" imported from the email alert "linkedin"
    And a job board named "Remote OK" imported from the feed "remoteok"
    When I open the inbox
    Then I can import the job boards: "Remote OK"

  # --- Discarding and restoring ---

  Scenario: Discard an offer with a reason
    Given an offer for "Acme" as "Backend Engineer"
    And I am on the inbox
    When I discard the offer "Backend Engineer" because "Not remote"
    Then I see that there are no offers
    And the "discarded" offers show "Backend Engineer" with reason "Not remote"

  Scenario: Undo a discard right away
    Given an offer for "Acme" as "Backend Engineer"
    And I am on the inbox
    And I discarded the offer "Backend Engineer"
    When I undo the discard
    Then I see the offers, in order: "Backend Engineer"

  Scenario: Restore a discarded offer later
    Given an offer for "Acme" as "Backend Engineer" that was discarded
    And I am on the inbox showing the "discarded" offers
    When I restore the offer "Backend Engineer"
    Then the "pending" offers show "Backend Engineer"

  # --- Promoting ---

  Scenario Outline: Promote an offer to an application
    Given an offer for "Acme" as "Backend Engineer"
    And I am on the inbox
    When I promote the offer "Backend Engineer" through "<channel>"
    Then I see the message "Application created"
    And the "promoted" offers show "Backend Engineer"

    Examples:
      | channel  |
      | portal   |
      | referral |

  Scenario: A promoted offer opens its application
    Given an offer for "Acme" as "Backend Engineer" that was promoted
    When I open the inbox showing the "promoted" offers
    Then the offer "Backend Engineer" links to its application

  Scenario: Only pending offers can be discarded or promoted
    Given an offer for "Acme" as "Backend Engineer" that was promoted
    When I open the inbox showing the "promoted" offers
    Then the offer "Backend Engineer" cannot be discarded or promoted
