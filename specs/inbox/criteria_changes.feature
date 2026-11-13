Feature: Criteria changes
  As a job seeker
  I want each change to my criteria kept with what it did, and to undo it
  So that I can tell later whether a change helped, and take it back if it did not

  A criteria change edits one rule of a search profile (its titles, keywords, excluded
  keywords, location or work modes) and is logged with what the rule was before and
  after, when it was made, what it did when applied (the counts of a preview,
  specs/inbox/criteria_previews.feature) and, when it came from an offer, which one.
  Editing a profile directly (specs/discovery/search_profiles.feature) is not logged.
  Undoing a change puts the rule back as it was and takes the change out of the log; a
  change whose rule was changed again later cannot be undone. The log lists the changes
  from the most recent.

  Background:
    Given a job board named "Remote OK" imported from the feed "remoteok"
    And a search profile named "Backend" with:
      | titles            | Backend Engineer |
      | excluded_keywords | Senior           |
    And the job board "Remote OK" was imported with:
      | title                 | company | description     | url                    |
      | Backend Engineer      | Acme    | Python services | https://remoteok.com/1 |
      | Backend Engineer Lead | Globex  | Python platform | https://remoteok.com/2 |
      | Data Engineer         | Initech | Spark pipelines | https://remoteok.com/3 |

  # --- Making a change ---

  Scenario: A change edits the rule and is logged with what it did
    When I change the profile "Backend" to have the excluded_keywords "Senior, Lead"
    Then the profile "Backend" has the excluded_keywords "Senior, Lead"
    And the log has 1 change, on the excluded_keywords of "Backend" from "Senior" to "Senior, Lead", that took 1 offer out of Pending

  Scenario: A change made from an offer says which one
    When I change the profile "Backend" to have the excluded_keywords "Senior, Lead" from the offer of "Globex"
    Then the latest change came from the offer of "Globex"

  Scenario: A change edits a single rule
    When I change the profile "Backend" to have the titles "Backend Engineer" and the keywords "Python"
    Then it is rejected as invalid

  Scenario: Cannot change a profile that does not exist
    When I change a nonexistent profile to have the keywords "Python"
    Then it is rejected because it does not exist

  # --- Listing ---

  Scenario: The log lists the changes from the most recent
    Given I changed the profile "Backend" to have the excluded_keywords "Senior, Lead"
    And I changed the profile "Backend" to have the titles "Backend Engineer, Data Engineer"
    When I list the changes
    Then the changes are, in order: "titles", "excluded_keywords"

  # --- Undoing ---

  Scenario: Undoing a change puts the rule back and takes it out of the log
    Given I changed the profile "Backend" to have the excluded_keywords "Senior, Lead"
    When I undo the latest change
    Then the profile "Backend" has the excluded_keywords "Senior"
    And the log is empty

  Scenario: Undoing a change leaves the other rules as they are
    Given I changed the profile "Backend" to have the excluded_keywords "Senior, Lead"
    And I changed the profile "Backend" to have the titles "Backend Engineer, Data Engineer"
    When I undo the change of the excluded_keywords
    Then the profile "Backend" has the excluded_keywords "Senior"
    And the profile "Backend" has the titles "Backend Engineer, Data Engineer"

  Scenario: A change whose rule was changed again cannot be undone
    Given I changed the profile "Backend" to have the excluded_keywords "Senior, Lead"
    And I changed the profile "Backend" to have the excluded_keywords "Senior, Lead, Staff"
    When I undo the change of the excluded_keywords to "Senior, Lead"
    Then it is rejected because the rule changed since

  Scenario: Cannot undo a change that does not exist
    When I undo a nonexistent change
    Then it is rejected because it does not exist
