Feature: Inbox screen
  As a job seeker
  I want to review the offers I collect from the job boards in one screen
  So that I triage each one without opening the API docs

  The rules of the offers (duplicates, statuses, promoting, feed limits) are those
  of specs/inbox/inbox.feature and specs/inbox/public_feeds.feature. This screen
  only shows them: every rejection appears as a message, next to its field when
  it belongs to one. The inbox opens with the pending offers, most recent first.

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

  # --- Importing feeds ---
  # @component: the E2E tests cannot reach the public feeds; component tests cover these.

  @component
  Scenario: Import a feed for a search profile
    Given a search profile named "Backend" with the title "Backend Engineer"
    And the feed "remoteok" publishes an offer for "Acme" as "Backend Engineer"
    And I am on the inbox
    When I import the feed "remoteok" for the profile "Backend"
    Then I see the import summary: 1 found, 1 matching, 1 added, 0 already in the inbox
    And I see the offers, in order: "Backend Engineer"

  @component
  Scenario: A feed imported too recently says when it can be imported again
    Given a search profile named "Backend" with the title "Backend Engineer"
    And the feed "remoteok" was imported 1 hour ago
    And I am on the inbox
    When I import the feed "remoteok" for the profile "Backend"
    Then I see that the feed "remoteok" can be imported again in 5 hours

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
