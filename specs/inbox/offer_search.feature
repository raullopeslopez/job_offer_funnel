Feature: Search the offers in the inbox
  As a job seeker
  I want to narrow the offers I list by a text and by the job board they came from
  So that I find a given offer, or review one company or one job board at a time

  The text matches the offers whose company or title contains it, ignoring case and
  the spaces around it; a blank text matches every offer. The job board matches the
  offers that came from it. Both narrow any other way of listing the offers (by status,
  filtered or not, near misses...), they narrow each other, and the total counts only
  the offers they match.

  Background:
    Given today is 2026-03-10
    And a job board named "LinkedIn"
    And a job board named "Remote OK"

  Scenario Outline: The text matches the company or the title, ignoring case
    Given an offer for "Acme" as "Backend Engineer"
    And an offer for "Globex" as "Data Engineer"
    And an offer for "Initech" as "Acme Platform Lead"
    When I list the offers searching for "<text>"
    Then the offers are, in order: "<titles>"
    And there are <total> offers in total

    Examples:
      | text     | titles                               | total |
      | acme     | Acme Platform Lead, Backend Engineer | 2     |
      | ENGINEER | Data Engineer, Backend Engineer      | 2     |
      | platform | Acme Platform Lead                   | 1     |
      | Umbrella |                                      | 0     |

  Scenario: The spaces around the text do not count
    Given an offer for "Acme" as "Backend Engineer"
    And an offer for "Globex" as "Data Engineer"
    When I list the offers searching for "  backend  "
    Then the offers are, in order: "Backend Engineer"

  Scenario: A blank text matches every offer
    Given an offer for "Acme" as "Backend Engineer"
    And an offer for "Globex" as "Data Engineer"
    When I list the offers searching for "   "
    Then there are 2 offers in total

  Scenario: The job board matches the offers that came from it
    Given an offer for "Acme" as "Backend Engineer" from "LinkedIn"
    And an offer for "Globex" as "Data Engineer" from "Remote OK"
    And an offer for "Initech" as "Platform Engineer"
    When I list the offers from "LinkedIn"
    Then the offers are, in order: "Backend Engineer"
    And there is 1 offer in total

  Scenario: A job board that does not exist matches no offer
    Given an offer for "Acme" as "Backend Engineer" from "LinkedIn"
    When I list the offers from a nonexistent job board
    Then there are 0 offers in total

  Scenario: The text and the job board narrow each other
    Given an offer for "Acme" as "Backend Engineer" from "LinkedIn"
    And an offer for "Acme" as "Data Engineer" from "Remote OK"
    And an offer for "Globex" as "Backend Developer" from "LinkedIn"
    When I list the offers from "LinkedIn" searching for "acme"
    Then the offers are, in order: "Backend Engineer"

  Scenario: The search narrows the offers of a status
    Given an offer for "Acme" as "Backend Engineer"
    And an offer for "Acme" as "Data Engineer" that was discarded
    And an offer for "Globex" as "Platform Engineer" that was discarded
    When I list the offers with status "discarded" searching for "acme"
    Then the offers are, in order: "Data Engineer"
    And there is 1 offer in total
