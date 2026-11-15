Feature: Inbox
  As a job seeker
  I want to collect the offers I find in the job boards in one place
  So that I review each one once and only the good ones enter the funnel

  An offer has the URL of the posting, the company and the job title as text,
  optionally the job board it came from, and optional notes. It is "pending" until
  it is "discarded" (with a reason; it can go back to pending) or
  "promoted" to an application. Offers do not count in the funnel metrics.
  The reason for a discard is one of a closed list: "title_word" (with the word of the
  title that does not fit), "stack", "location", "contract", "company" or "none", the
  one given when no other is. "expired" is only set by the imports.
  The same company and title, ignoring case and extra spaces, is the same offer,
  even if it was discarded: the same posting found in another job board is rejected.
  So is the same URL, ignoring a trailing slash and its utm_* parameters, even with
  another company or title: a company that edits the title keeps its posting's URL.
  Promoting creates an application in stage "evaluated" with the offer's URL and the
  title as role, for the company with that name (created if it does not exist yet),
  through channel "portal" unless another one is given.

  Background:
    Given today is 2026-03-10

  # --- Adding ---

  Scenario: Add an offer
    Given a job board named "LinkedIn"
    When I add an offer with:
      | url       | https://jobs.example/1         |
      | company   | Acme                           |
      | title     | Backend Engineer               |
      | job_board | LinkedIn                       |
      | notes     | Found through a saved search   |
    Then the offer has:
      | url       | https://jobs.example/1         |
      | company   | Acme                           |
      | title     | Backend Engineer               |
      | job_board | LinkedIn                       |
      | notes     | Found through a saved search   |
      | status    | pending                        |

  Scenario: Add an offer with only the required fields
    When I add an offer for "Acme" as "Backend Engineer"
    Then the offer is "pending"
    And the offer has no job board

  Scenario Outline: An offer needs valid data
    When I add an offer for "Acme" as "Backend Engineer" with "<field>" set to "<value>"
    Then it is rejected as invalid

    Examples:
      | field   | value     |
      | url     | not-a-url |
      | company |           |
      | title   |           |

  Scenario: Cannot add an offer from a job board that does not exist
    When I add an offer for "Acme" as "Backend Engineer" from a nonexistent job board
    Then it is rejected because the job board does not exist

  Scenario Outline: The same company and title is the same offer, ignoring case and extra spaces
    Given an offer for "Acme" as "Backend Engineer"
    When I add an offer for "<company>" as "<title>"
    Then it is rejected because the offer already exists

    Examples:
      | company | title              |
      | Acme    | Backend Engineer   |
      | ACME    | backend engineer   |
      | Acme    | Backend   Engineer |

  Scenario: A discarded offer is still a duplicate
    Given an offer for "Acme" as "Backend Engineer" that was discarded
    When I add an offer for "Acme" as "Backend Engineer"
    Then it is rejected because the offer already exists

  Scenario Outline: The same URL is the same offer, ignoring a trailing slash and utm_* parameters
    Given an offer for "Acme" as "Backend Engineer" with URL "https://jobs.example/1"
    When I add an offer for "Acme" as "Senior Backend Engineer" with URL "<url>"
    Then it is rejected because the offer already exists

    Examples:
      | url                                         |
      | https://jobs.example/1                      |
      | https://jobs.example/1/                     |
      | https://jobs.example/1?utm_source=api       |

  Scenario: Another query string is another URL
    Given an offer for "Acme" as "Backend Engineer" with URL "https://jobs.example/apply?job=1"
    When I add an offer for "Acme" as "Senior Backend Engineer" with URL "https://jobs.example/apply?job=2"
    Then the offer is "pending"

  # --- Viewing and listing ---

  Scenario: Cannot view an offer that does not exist
    When I view a nonexistent offer
    Then it is rejected because the offer does not exist

  Scenario: Offers are listed from the most recently added
    Given offers for "Acme" as "A", "B" and "C", added in that order
    When I list the offers
    Then the offers are, in order: "C", "B", "A"
    And there are 3 offers in total

  Scenario Outline: Filter the offers by status
    Given an offer for "Acme" as "Pending one"
    And an offer for "Acme" as "Discarded one" that was discarded
    And an offer for "Acme" as "Promoted one" that was promoted
    When I list the offers with status "<status>"
    Then the offers are, in order: "<title>"

    Examples:
      | status    | title         |
      | pending   | Pending one   |
      | discarded | Discarded one |
      | promoted  | Promoted one  |

  # --- Discarding ---

  Scenario Outline: Discard an offer with a reason
    Given an offer for "Acme" as "Backend Engineer"
    When I discard it because "<reason>"
    Then the offer is "discarded" with reason "<reason>" and no word

    Examples:
      | reason   |
      | stack    |
      | location |
      | contract |
      | company  |
      | none     |

  Scenario: Discard an offer because of a word in its title
    Given an offer for "Acme" as "Senior Backend Engineer"
    When I discard it because of the word "Senior"
    Then the offer is "discarded" with reason "title_word" and word "Senior"

  Scenario: Discard an offer without saying why
    Given an offer for "Acme" as "Backend Engineer"
    When I discard it
    Then the offer is "discarded" with reason "none" and no word

  Scenario Outline: A discard needs a reason of the list, and a word only with title_word
    Given an offer for "Acme" as "Senior Backend Engineer"
    When I discard it because "<reason>" with the word "<word>"
    Then it is rejected as invalid

    Examples:
      | reason     | word   |
      | Not remote |        |
      | expired    |        |
      | title_word |        |
      | stack      | Senior |

  Scenario: The word of a discard must be a word of the title
    Given an offer for "Acme" as "Senior Backend Engineer"
    When I discard it because of the word "Junior"
    Then it is rejected because the word is not in the title

  Scenario: A discarded offer can go back to pending, without its reason
    Given an offer for "Acme" as "Senior Backend Engineer"
    And I discarded it because of the word "Senior"
    When I restore it
    Then the offer is "pending" with no reason and no word

  Scenario Outline: Only a pending offer can be discarded, and only a discarded one restored
    Given an offer for "Acme" as "Backend Engineer" that was <state>
    When I <action> it
    Then it is rejected because the offer is not in a valid status

    Examples:
      | state     | action  |
      | discarded | discard |
      | promoted  | discard |
      | promoted  | restore |

  Scenario: An offer that is pending cannot be restored
    Given an offer for "Acme" as "Backend Engineer"
    When I restore it
    Then it is rejected because the offer is not in a valid status

  # --- Promoting ---

  Scenario: Promote an offer to an application
    Given an offer for "Acme" as "Backend Engineer" with URL "https://jobs.example/1"
    When I promote it
    Then the offer is "promoted"
    And its application is in stage "evaluated" for "Acme" as "Backend Engineer" through "portal" with URL "https://jobs.example/1"
    And its application's history starts on 2026-03-10

  Scenario: Promote an offer through another channel
    Given an offer for "Acme" as "Backend Engineer"
    When I promote it through "referral"
    Then its application is through "referral"

  Scenario: Promoting uses the company that already has that name, ignoring case
    Given a company named "ACME"
    And an offer for "acme" as "Backend Engineer"
    When I promote it
    Then its application is for the company "ACME"
    And there is 1 company in total

  Scenario: Promoting creates the company when it does not exist
    Given an offer for "Acme" as "Backend Engineer"
    When I promote it
    Then there is a company named "Acme"

  Scenario Outline: Only a pending offer can be promoted
    Given an offer for "Acme" as "Backend Engineer" that was <state>
    When I promote it
    Then it is rejected because the offer is not in a valid status

    Examples:
      | state     |
      | discarded |
      | promoted  |

  Scenario: Cannot promote an offer that does not exist
    When I promote a nonexistent offer
    Then it is rejected because the offer does not exist

  # --- Job boards in use ---

  Scenario: A job board with offers cannot be deleted
    Given a job board named "LinkedIn"
    And an offer for "Acme" as "Backend Engineer" from "LinkedIn"
    When I delete the job board "LinkedIn"
    Then it is rejected because the job board has offers
