Feature: Criteria previews
  As a job seeker
  I want to see what a change to a search profile would do before I save it
  So that I never lose good offers by filtering more than I meant to

  A preview takes the same changes as editing a profile (its titles, keywords, excluded
  keywords, location and work modes) and saves nothing. It checks the imported offers
  against the profiles as they are and as they would be with the change, with the same
  rules that filter the pending ones (specs/inbox/filtered_offers.feature), and says:
  - how many pending offers would come into Pending (they are filtered now and would not be),
  - how many would leave it (they are not filtered now and would be),
  - how many promoted offers, and how many discarded ones, the change would have filtered:
    they fit the profiles now and would not with the change;
  - how many discarded offers the change would make fit: they do not fit the profiles now
    and would with the change.
  Offers added by hand are never filtered, so they never count. Expired offers do not
  count: the import discarded them, not the user. Applying the change is editing the
  profile as usual.

  Background:
    Given a job board named "Remote OK" imported from the feed "remoteok"
    And a search profile named "Backend" with:
      | titles            | Backend Engineer |
      | keywords          | Python           |
      | excluded_keywords | Senior           |
    And the job board "Remote OK" was imported with:
      | title                   | company | description      | url                    |
      | Backend Engineer        | Acme    | Python services  | https://remoteok.com/1 |
      | Data Engineer           | Globex  | Python pipelines | https://remoteok.com/2 |
      | Senior Backend Engineer | Initech | Python services  | https://remoteok.com/3 |
      | Backend Engineer Lead   | Hooli   | Python platform  | https://remoteok.com/4 |

  # --- Pending ---

  Scenario Outline: A preview says how many offers would come into Pending and leave it
    When I preview the profile "Backend" with the <field> "<words>"
    Then <entering> offers would come into Pending and <leaving> would leave it

    Examples:
      | field             | words                           | entering | leaving |
      | titles            | Backend Engineer, Data Engineer | 1        | 0       |
      | excluded_keywords | Senior, Lead                    | 0        | 1       |
      | excluded_keywords |                                 | 1        | 0       |
      | keywords          | Python, Django                  | 0        | 2       |
      | work_modes        | onsite                          | 0        | 0       |

  Scenario: An offer that still fits another profile does not leave Pending
    Given a search profile named "Leads" with:
      | titles | Lead |
    When I preview the profile "Backend" with the excluded_keywords "Senior, Lead"
    Then 0 offers would come into Pending and 0 would leave it

  Scenario: A preview saves nothing
    Given I previewed the profile "Backend" with the excluded_keywords "Senior, Lead"
    When I view the offer of "Hooli"
    Then the offer is not filtered

  Scenario Outline: A preview matches saving the change
    Given I previewed the profile "Backend" with the <field> "<words>"
    When I edit the profile "Backend" to have the <field> "<words>"
    Then the pending offers that came in and left match the preview

    Examples:
      | field             | words                           |
      | titles            | Backend Engineer, Data Engineer |
      | excluded_keywords | Senior, Lead                    |
      | keywords          | Python, Django                  |

  # --- Promoted and discarded ---

  Scenario: A preview says how many promoted and discarded offers the change would have filtered
    Given I promoted the offer of "Acme"
    And I promoted the offer of "Globex"
    And I discarded the offer of "Hooli"
    When I preview the profile "Backend" with the keywords "Python, Django"
    Then the change would have filtered 1 offer I promoted and 1 I discarded

  Scenario: A preview says how many discarded offers the change would make fit
    Given I discarded the offer of "Initech"
    When I preview the profile "Backend" with the excluded_keywords ""
    Then 1 offer I discarded would fit with the change

  Scenario: Expired offers and offers added by hand do not count
    Given an offer for "Umbrella" as "Backend Engineer"
    And I discarded the offer of "Umbrella"
    And the job board "Remote OK" was imported again without the offer of "Hooli"
    When I preview the profile "Backend" with the keywords "Python, Django"
    Then the change would have filtered 0 offers I promoted and 0 I discarded

  # --- Errors ---

  Scenario: Cannot preview a profile that does not exist
    When I preview a nonexistent profile with the keywords "Python"
    Then it is rejected because the profile does not exist

  Scenario: Cannot preview a profile without titles
    When I preview the profile "Backend" with the titles ""
    Then it is rejected as invalid
