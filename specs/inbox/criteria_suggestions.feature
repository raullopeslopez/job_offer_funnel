Feature: Criteria suggestions
  As a job seeker
  I want the app to suggest excluding the words I keep discarding
  So that my criteria learn from my decisions without me telling them anything extra

  The suggestions only count; no language model is involved. A word of the titles is
  suggested as an exclusion of a search profile when:
  - it is in the titles of at least 3 discarded offers (imported, and not expired),
  - it is in the title of no promoted offer,
  - the profile does not exclude it yet, and it is not part of the profile's titles or
    keywords,
  - excluding it would have filtered at least one of those discarded offers (they fit
    the profile now).
  Words are compared ignoring case. Each suggestion says in how many of the discarded
  offers the word is, out of all of them, which offers those are and what excluding it
  would do (specs/inbox/criteria_previews.feature). "Not now" hides a suggestion for good;
  accepting it is a criteria change (specs/inbox/criteria_changes.feature). Nothing is
  ever applied on its own. The offer triager may also suggest excluding a word, with why
  (specs/inbox/offer_triages.feature): those join the list, marked as from the triager,
  after the counted ones.

  Background:
    Given a job board named "Remote OK" imported from the feed "remoteok"
    And a search profile named "Backend" with:
      | titles | Backend Engineer |
    And the job board "Remote OK" was imported with:
      | title                  | company  | description     | url                    |
      | Backend Engineer Lead  | Acme     | Python services | https://remoteok.com/1 |
      | Lead Backend Engineer  | Globex   | Python platform | https://remoteok.com/2 |
      | Backend Engineer, Lead | Initech  | Go services     | https://remoteok.com/3 |
      | Backend Engineer       | Hooli    | Python services | https://remoteok.com/4 |
      | Lead Backend Engineer  | Umbrella | Rust services   | https://remoteok.com/5 |

  Scenario: A word in 3 discarded offers and in no promoted one is suggested
    Given I discarded the offers of "Acme", "Globex" and "Initech"
    When I list the suggestions
    Then the only suggestion is to exclude "Lead" from "Backend", in 3 of the 3 discarded
    And it takes 1 offer out of Pending and loses none I promoted
    And it is backed by the offers of "Acme", "Globex" and "Initech"

  Scenario: A word in fewer than 3 discarded offers is not suggested
    Given I discarded the offers of "Acme" and "Globex"
    When I list the suggestions
    Then there are no suggestions

  Scenario: A word in a promoted offer is not suggested
    Given I discarded the offers of "Acme", "Globex" and "Initech"
    And I promoted the offer of "Umbrella"
    When I list the suggestions
    Then there are no suggestions

  Scenario: A word the profile already excludes is not suggested
    Given I discarded the offers of "Acme", "Globex" and "Initech"
    And the profile "Backend" excludes "lead"
    When I list the suggestions
    Then there are no suggestions

  Scenario: A word that would filter none of those offers for a profile is not suggested for it
    Given a search profile named "Data" with:
      | titles | Data Engineer |
    And I discarded the offers of "Acme", "Globex" and "Initech"
    When I list the suggestions
    Then the only suggestion is to exclude "Lead" from "Backend", in 3 of the 3 discarded

  # --- Not now ---

  Scenario: "Not now" hides a suggestion for good
    Given I discarded the offers of "Acme", "Globex" and "Initech"
    And I said "Not now" to excluding "Lead" from "Backend"
    When I list the suggestions
    Then there are no suggestions

  Scenario: Saying "Not now" twice is the same as once
    Given I discarded the offers of "Acme", "Globex" and "Initech"
    And I said "Not now" to excluding "Lead" from "Backend"
    When I say "Not now" to excluding "lead" from "Backend"
    Then it is accepted

  Scenario: Cannot say "Not now" for a profile that does not exist
    When I say "Not now" to excluding "Lead" from a nonexistent profile
    Then it is rejected because it does not exist
