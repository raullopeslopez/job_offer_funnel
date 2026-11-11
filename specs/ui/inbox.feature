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

  Background:
    Given I am signed in with a valid token

  # --- Viewing ---

  Scenario: The inbox shows the pending offers, most recent first
    Given offers for "Acme" as "A", "B" and "C", added in that order
    And an offer for "Acme" as "Discarded one" that was discarded
    When I open the inbox
    Then I see the offers, in order: "C", "B", "A"
    And I see 3 offers in total

  Scenario Outline: Show the offers of another status
    Given an offer for "Acme" as "Pending one"
    And an offer for "Acme" as "Discarded one" that was discarded
    And an offer for "Acme" as "Promoted one" that was promoted
    When I open the inbox showing the "<status>" offers
    Then I see the offers, in order: "<title>"

    Examples:
      | status    | title         |
      | pending   | Pending one   |
      | discarded | Discarded one |
      | promoted  | Promoted one  |

  # @component: only an import makes filtered offers, and the E2E tests cannot reach the feeds.

  @component
  Scenario: The filtered offers have their own view
    Given a search profile named "Backend" with the title "Backend Engineer"
    And the job board "Remote OK" was imported with an offer for "Acme" as "Backend Engineer"
    And the job board "Remote OK" was imported with an offer for "Globex" as "Data Engineer"
    When I open the inbox showing the "filtered" offers
    Then I see the offers, in order: "Data Engineer"

  @component
  Scenario: The pending view leaves out the filtered offers
    Given a search profile named "Backend" with the title "Backend Engineer"
    And the job board "Remote OK" was imported with an offer for "Acme" as "Backend Engineer"
    And the job board "Remote OK" was imported with an offer for "Globex" as "Data Engineer"
    When I open the inbox
    Then I see the offers, in order: "Backend Engineer"

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
    And I see 1 offers in total

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

  Scenario: Only pending offers can be discarded or promoted
    Given an offer for "Acme" as "Backend Engineer" that was promoted
    When I open the inbox showing the "promoted" offers
    Then the offer "Backend Engineer" cannot be discarded or promoted
