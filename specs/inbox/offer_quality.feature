Feature: Offer quality
  As a job seeker
  I want to measure whether what reaches Pending is worth my time, and whether what is
  worth my time reaches Pending
  So that each change to my criteria is judged by its results, not by a hunch

  The quality covers the offers added in the last 4 weeks (28 days up to today), and each
  figure also comes week by week, from the oldest of the 4 weeks to the current one. An
  offer counts in the week it was added. A rate is a percentage with one decimal, or
  nothing when there is nothing to divide by.
  - Precision: of the offers decided from Pending, the promoted ones over the promoted and
    discarded ones. Rescues (specs/inbox/rescues.feature) were decided from Filtered, and
    expired offers were discarded by the import, not by the user: neither counts.
  - Losses: of the near misses reviewed, the share rescued, and how many near misses are
    still to review.
  - Flow: the imported offers that fit the profiles as they are now, per week and on
    average over the 4 weeks.
  - Real result: of the promoted offers, how many applications reached `applied` and how
    many got an answer (reached `screening`).
  - Discards by reason, the most frequent first, without the expired ones.
  - By source (a job board or a watched company): the imported offers, how many fit, and
    how many were promoted and discarded.
  - The triager (specs/inbox/offer_triages.feature), over the triaged offers I promoted or
    discarded: its precision, the suggested discards I discarded over the suggested
    discards I decided; and its misses, the missed discards (offers it marked OK) over the
    triaged offers I discarded. Over the near misses it triaged and I reviewed
    (specs/inbox/near_miss_triages.feature): its rescues, the OK ones I rescued over the
    OK ones I reviewed; and its lost rescues, the KO ones I rescued over those I rescued.

  Background:
    Given a job board named "Remote OK" imported from the feed "remoteok"
    And a search profile named "Backend" with:
      | titles   | Backend Engineer |
      | keywords | Python           |
    And the job board "Remote OK" was imported with:
      | title            | company  | description              | url                    |
      | Backend Engineer | Acme     | Python services          | https://remoteok.com/1 |
      | Backend Engineer | Globex   | Python services          | https://remoteok.com/2 |
      | Backend Engineer | Initech  | Python services          | https://remoteok.com/3 |
      | Backend Engineer | Hooli    | Go services for payments | https://remoteok.com/4 |
      | Data Engineer    | Umbrella | Go pipelines             | https://remoteok.com/5 |

  # --- Precision ---

  Scenario: Precision is the share of promoted offers among those decided from Pending
    Given I promoted the offer of "Acme"
    And I discarded the offer of "Globex" because "stack"
    And I discarded the offer of "Initech" because "location"
    When I view the offer quality
    Then the precision is 33.3% of 3 decided offers

  Scenario: Rescues and expired offers do not count in the precision
    Given I promoted the offer of "Acme"
    And I promoted the offer of "Hooli"
    And the job board "Remote OK" was imported again without the offer of "Globex"
    When I view the offer quality
    Then the precision is 100.0% of 1 decided offer

  Scenario: Without decided offers there is no precision
    When I view the offer quality
    Then there is no precision

  # --- Losses ---

  Scenario: Losses are the share of near misses reviewed that were rescued
    Given I promoted the offer of "Hooli"
    When I view the offer quality
    Then the losses are 100.0% of 1 reviewed near miss, with 0 left to review

  Scenario: Near misses marked rightly filtered are reviewed, not rescued
    Given I marked the offer of "Hooli" as rightly filtered
    When I view the offer quality
    Then the losses are 0.0% of 1 reviewed near miss, with 0 left to review

  Scenario: Without reviews there are no losses, only near misses to review
    When I view the offer quality
    Then there are no losses, with 1 near miss left to review

  # --- Flow ---

  Scenario: Flow counts the imported offers that fit the profiles now
    Given an offer for "Wayne" as "Backend Engineer"
    When I view the offer quality
    Then 3 offers fit this week and 0.8 a week on average

  # --- Real result ---

  Scenario: Real result follows the applications of the promoted offers
    Given I promoted the offer of "Acme"
    And I promoted the offer of "Globex"
    And I promoted the offer of "Initech"
    And the application for "Acme" moved to "applied"
    And the application for "Globex" moved to "screening"
    When I view the offer quality
    Then of 3 promoted offers, 2 reached applied and 1 got an answer

  # --- Discards and sources ---

  Scenario: Discards are counted by reason, the most frequent first
    Given I discarded the offer of "Acme" because "stack"
    And I discarded the offer of "Globex" because "location"
    And I discarded the offer of "Initech" because "stack"
    And the job board "Remote OK" was imported again without the offer of "Hooli"
    When I view the offer quality
    Then the discards by reason are:
      | reason   | offers |
      | stack    | 2      |
      | location | 1      |

  Scenario: Each source says what it brought and what became of it
    Given I promoted the offer of "Acme"
    And I discarded the offer of "Globex" because "stack"
    And an offer for "Wayne" as "Backend Engineer"
    When I view the offer quality
    Then the sources are:
      | source    | imported | fitting | promoted | discarded |
      | Remote OK | 5        | 3       | 1        | 1         |

  # --- Triager ---

  Scenario: The triager's precision and misses follow what I did with the triaged offers
    Given the offer triager says the offer of "Acme" is KO, with the reason "stack" and the evidence "Python services"
    And the offer triager says the offer of "Globex" is KO, with the reason "stack" and the evidence "Python services"
    And the offer triager says the offer of "Initech" is OK
    And I triaged the offers
    And I discarded the offer of "Acme" because "stack"
    And I promoted the offer of "Globex"
    And I discarded the offer of "Initech" because "location"
    When I view the offer quality
    Then the triager's precision is 50.0% of 2 suggested discards decided
    And the triager's misses are 50.0% of 2 triaged offers discarded

  Scenario: The triager's rescues and lost rescues follow what I did with the near misses
    Given the job board "Remote OK" was imported with:
      | title            | company  | description              | url                    |
      | Backend Engineer | Wayne    | Go services for payments | https://remoteok.com/6 |
      | Backend Engineer | Umbrella | Go services for payments | https://remoteok.com/7 |
    And the offer triager says the offers of "Hooli" and "Wayne" are OK, quoting their descriptions
    And the offer triager says the offer of "Umbrella" is KO because "Not for you."
    And I triaged the offers
    And I triaged the offers again, past the first 5
    And I promoted the offer of "Hooli"
    And I marked the offer of "Wayne" as rightly filtered
    And I promoted the offer of "Umbrella"
    When I view the offer quality
    Then the triager's rescues are 50.0% of 2 OK near misses reviewed
    And the triager's lost rescues are 50.0% of 2 near misses rescued

  Scenario: Without triaged offers decided there are no triager figures
    Given I triaged the offers
    When I view the offer quality
    Then there is no triager precision and there are no triager misses
