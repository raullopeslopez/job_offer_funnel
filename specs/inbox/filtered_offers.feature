Feature: Filtered offers
  As a job seeker
  I want the imported offers that fit none of my search profiles kept apart, not lost
  So that a badly written profile hides offers I can still find and fix

  Imports keep every offer their source returns (specs/inbox/public_feeds.feature and
  specs/inbox/ats_companies.feature). A pending imported offer is filtered when it fits
  none of the search profiles. It fits a profile when:
  - one of the profile's titles appears in the offer's title,
  - all of its keywords appear in the title or the description,
  - none of its excluded keywords appears in the title.
  Words are compared ignoring case. Whether an offer is filtered always follows the
  current profiles: creating, editing or deleting a profile changes it at once.
  Offers added by hand are never filtered. A filtered offer is still pending: it can be
  discarded or promoted like any other.

  Background:
    Given the time is 2026-03-10 09:00
    And a search profile named "Backend" with:
      | titles            | Backend Engineer, Python Developer |
      | keywords          | Python                             |
      | excluded_keywords | Senior                             |

  # --- Fitting a profile ---

  Scenario Outline: An imported offer fits when a title, every keyword and no exclusion fit
    Given the feed "remoteok" was imported with:
      | title   | company | description   | url                    |
      | <title> | Acme    | <description> | https://remoteok.com/1 |
    When I view the offer "<title>"
    Then the offer is <filtered>

    Examples:
      | title                     | description                 | filtered     |
      | Backend Engineer          | Python services             | not filtered |
      | backend engineer (Remote) | We love python              | not filtered |
      | Backend Engineer, Python  | Go services                 | not filtered |
      | Backend Engineer          | Python, mentor senior staff | not filtered |
      | Backend Engineer          | Go services                 | filtered     |
      | Data Engineer             | Python pipelines            | filtered     |
      | Senior Backend Engineer   | Python services             | filtered     |

  Scenario: An offer that fits any profile is not filtered
    Given a search profile named "Data" with:
      | titles | Data Engineer |
    And the board of the watched company "Acme" was imported with:
      | title         | description      | url                                  |
      | Data Engineer | Spark pipelines  | https://boards.greenhouse.io/acme/1 |
    When I view the offer "Data Engineer"
    Then the offer is not filtered

  Scenario: Without search profiles every imported offer is filtered
    Given there are no search profiles
    And the feed "remoteok" was imported with:
      | title            | company | description     | url                    |
      | Backend Engineer | Acme    | Python services | https://remoteok.com/1 |
    When I view the offer "Backend Engineer"
    Then the offer is filtered

  Scenario: An offer added by hand is never filtered
    Given an offer for "Acme" as "Frontend Engineer"
    When I view the offer "Frontend Engineer"
    Then the offer is not filtered

  # --- Following the profiles ---

  Scenario: Editing a profile so an offer fits takes it out of the filtered ones
    Given the feed "remoteok" was imported with:
      | title         | company | description      | url                    |
      | Data Engineer | Acme    | Python pipelines | https://remoteok.com/1 |
    And I edit the profile "Backend" to have the titles "Backend Engineer, Data Engineer"
    When I view the offer "Data Engineer"
    Then the offer is not filtered

  Scenario: Deleting the only profile an offer fits filters it
    Given the feed "remoteok" was imported with:
      | title            | company | description     | url                    |
      | Backend Engineer | Acme    | Python services | https://remoteok.com/1 |
    And I delete the profile "Backend"
    When I view the offer "Backend Engineer"
    Then the offer is filtered

  # --- Listing ---

  Scenario Outline: List the pending offers that are filtered or not
    Given the feed "remoteok" was imported with:
      | title            | company | description     | url                    |
      | Backend Engineer | Acme    | Python services | https://remoteok.com/1 |
      | Data Engineer    | Globex  | Spark pipelines | https://remoteok.com/2 |
    And an offer for "Initech" as "Frontend Engineer"
    When I list the pending offers that are <filtered>
    Then the offers are, in order: <titles>

    Examples:
      | filtered     | titles                                   |
      | filtered     | "Data Engineer"                          |
      | not filtered | "Frontend Engineer", "Backend Engineer"  |

  Scenario: Only pending offers are filtered
    Given the feed "remoteok" was imported with:
      | title         | company | description     | url                    |
      | Data Engineer | Globex  | Spark pipelines | https://remoteok.com/1 |
    And I discarded the offer "Data Engineer"
    When I view the offer "Data Engineer"
    Then the offer is not filtered

  # --- Acting on a filtered offer ---

  Scenario Outline: A filtered offer can be discarded or promoted
    Given the feed "remoteok" was imported with:
      | title         | company | description     | url                    |
      | Data Engineer | Globex  | Spark pipelines | https://remoteok.com/1 |
    When I <action> the offer "Data Engineer"
    Then the offer "Data Engineer" is "<status>"

    Examples:
      | action  | status    |
      | discard | discarded |
      | promote | promoted  |
