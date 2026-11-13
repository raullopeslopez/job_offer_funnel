Feature: Rescues and rightly filtered offers
  As a job seeker
  I want the app to note which filtered offers I promote and which I leave filtered
  So that I learn how much good the filter hides without telling it anything extra

  Promoting a filtered offer (specs/inbox/filtered_offers.feature) is a rescue: the offer
  keeps the rules that filtered it at that moment (specs/inbox/filter_reasons.feature).
  A filtered offer can also be marked "rightly filtered": it stays pending and filtered,
  but it is reviewed, so it is no longer a near miss. The mark can be undone, and
  promoting the offer later turns it into a rescue. Both are reviews; a review keeps
  whether the offer was a near miss when it was made (it failed one rule, not the title),
  so the near misses reviewed and rescued can be counted at any time.

  Background:
    Given a job board named "Remote OK" imported from the feed "remoteok"
    And a search profile named "Backend" with:
      | titles            | Backend Engineer |
      | keywords          | Python           |
      | excluded_keywords | Senior           |
    And the job board "Remote OK" was imported with:
      | title            | company | description     | url                    |
      | Backend Engineer | Acme    | Go services     | https://remoteok.com/1 |
      | Backend Engineer | Globex  | Go services     | https://remoteok.com/2 |
      | Data Engineer    | Initech | Go pipelines    | https://remoteok.com/3 |
      | Backend Engineer | Hooli   | Python services | https://remoteok.com/4 |

  # --- Rescues ---

  Scenario Outline: Promoting a filtered offer is a rescue, with the rules that filtered it
    When I promote the offer of "<company>"
    Then the offer of "<company>" is "rescued" with the rules <rules>

    Examples:
      | company | rules                 |
      | Acme    | "keywords"            |
      | Initech | "title", "keywords"   |

  Scenario Outline: Promoting an offer that is not filtered is not a rescue
    Given an offer for "Umbrella" as "Frontend Engineer"
    When I promote the offer of "<company>"
    Then the offer of "<company>" has no review

    Examples:
      | company  |
      | Hooli    |
      | Umbrella |

  # --- Rightly filtered ---

  Scenario: A filtered offer marked rightly filtered stays filtered, and is no longer a near miss
    When I mark the offer of "Acme" as rightly filtered
    Then the offer of "Acme" is "rightly_filtered" with the rules "keywords"
    And the offer of "Acme" is "pending" and filtered
    And the near misses are the offers of: "Globex"

  Scenario Outline: Only a filtered offer can be marked rightly filtered
    Given an offer for "Umbrella" as "Frontend Engineer"
    And I discarded the offer of "Globex"
    When I mark the offer of "<company>" as rightly filtered
    Then it is rejected because the offer is not filtered

    Examples:
      | company  |
      | Hooli    |
      | Umbrella |
      | Globex   |

  Scenario: Cannot mark an offer that does not exist
    When I mark a nonexistent offer as rightly filtered
    Then it is rejected because the offer does not exist

  Scenario: Undoing the mark makes the offer a near miss again
    Given I marked the offer of "Acme" as rightly filtered
    When I undo the mark of the offer of "Acme"
    Then the offer of "Acme" has no review
    And the near misses are the offers of: "Globex", "Acme"

  Scenario: Promoting an offer marked rightly filtered rescues it
    Given I marked the offer of "Acme" as rightly filtered
    When I promote the offer of "Acme"
    Then the offer of "Acme" is "rescued" with the rules "keywords"

  # --- Counting ---

  Scenario: Count the near misses reviewed and those rescued
    Given I promoted the offer of "Acme"
    And I marked the offer of "Globex" as rightly filtered
    And I promoted the offer of "Initech"
    When I count the filtered offers
    Then 2 near misses were reviewed and 1 was rescued
