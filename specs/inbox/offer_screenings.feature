Feature: Offer screenings
  As a job seeker
  I want a language model to compare each pending offer, description included, with what I decided before
  So that the offers I would discard are pointed out to me, while I keep the last word

  Screening sends the offer screener, one at a time, up to 5 pending imported offers that
  fit a search profile, have a description and were not screened yet, from the most
  recently added. For each one it is told the offer's title, company and description,
  the search profiles (name, titles, keywords and excluded keywords) and my last 30
  promoted and last 30 discarded imported offers, from the most recent: their title and,
  for the discarded ones, the discard reason and its word. Expired offers are not
  decisions and are not told.
  The screener answers with nothing to say, or with a suggested discard: a reason of the
  list (title_word, stack, location, contract or company) and its evidence. For title_word
  the evidence is the word, which must be a word of the title; for the other reasons it is
  a sentence of the description, letter for letter. Any other answer is not kept. Either
  way the offer is screened and is not screened again.
  A suggested discard is never applied on its own: the offer stays pending, and
  discarding it with that reason and word is a normal discard
  (specs/inbox/inbox.feature). Without an offer screener the app offers no screening and
  works as always. An offer the screener fails on is left to be screened again.

  Background:
    Given a job board named "Remote OK" imported from the feed "remoteok"
    And a search profile named "Backend" with:
      | titles | Backend Engineer |
    And the job board "Remote OK" was imported with:
      | title                 | company | description                              | url                    |
      | Backend Engineer      | Acme    | Python services for a crypto exchange.   | https://remoteok.com/1 |
      | Backend Engineer      | Globex  | Go services. Part-time, 20 hours a week. | https://remoteok.com/2 |
      | Backend Engineer Lead | Initech | Python platform.                         | https://remoteok.com/3 |
      | Data Engineer         | Hooli   | Spark pipelines.                         | https://remoteok.com/4 |

  # --- Suggested discards ---

  Scenario Outline: A suggested discard with its evidence is kept, and the offer stays pending
    Given the offer screener answers for the offer of "<company>" with the reason "<reason>" and the evidence "<evidence>"
    When I screen the offers
    Then the offer of "<company>" has a suggested discard because "<reason>" with "<evidence>"
    And the offer of "<company>" is "pending"

    Examples:
      | company | reason     | evidence                   |
      | Globex  | contract   | Part-time, 20 hours a week |
      | Acme    | company    | for a crypto exchange      |
      | Initech | title_word | lead                       |

  Scenario Outline: An answer without its evidence is not kept
    Given the offer screener answers for the offer of "<company>" with the reason "<reason>" and the evidence "<evidence>"
    When I screen the offers
    Then the offer of "<company>" has no suggested discard
    And the screening screened 3 offers, failed on 0 and left 0

    Examples:
      | company | reason     | evidence    |
      | Globex  | contract   | Full-time   |
      | Globex  | title_word | Senior      |
      | Initech | title_word | Lea         |
      | Initech | title_word | Python      |
      | Acme    | none       | crypto      |
      | Acme    | expired    | crypto      |

  Scenario: An offer the screener has nothing to say about has no suggested discard
    When I screen the offers
    Then the offer of "Acme" has no suggested discard
    And the screening screened 3 offers, failed on 0 and left 0

  # --- Which offers are screened ---

  Scenario: Only pending imported offers that fit and were not screened yet are screened
    Given an offer for "Umbrella" as "Backend Engineer"
    And I discarded the offer of "Initech"
    When I screen the offers
    Then the offer screener was asked only about the offers of "Acme" and "Globex"

  Scenario: An offer is screened once
    Given I screened the offers
    When I screen the offers
    Then the screening screened 0 offers, failed on 0 and left 0

  Scenario: At most 5 offers are screened at a time
    Given the job board "Remote OK" was imported with 4 more offers as "Backend Engineer"
    When I screen the offers
    Then the screening screened 5 offers, failed on 0 and left 2

  # --- What the screener is told ---

  Scenario: The screener is told the profiles and my decisions, not the expired ones
    Given I promoted the offer of "Initech"
    And I discarded the offer of "Hooli" because "stack"
    And the job board "Remote OK" was imported again without the offer of "Globex"
    When I screen the offers
    Then the offer screener was told the profile "Backend" and these decisions:
      | title                 | decision  | reason | word |
      | Backend Engineer Lead | promoted  |        |      |
      | Data Engineer         | discarded | stack  |      |

  # --- Without a screener, and when it fails ---

  Scenario Outline: The screening is offered only with an offer screener
    Given the offer screener is <screener>
    When I check whether the screening is available
    Then it is <availability>

    Examples:
      | screener   | availability  |
      | configured | available     |
      | missing    | not available |

  Scenario: Cannot screen without an offer screener
    Given the offer screener is missing
    When I screen the offers
    Then it is rejected because the offer screener is not available
    And the offer of "Acme" has no suggested discard

  Scenario: An offer the screener fails on is left to be screened again
    Given the offer screener fails on the offer of "Globex"
    When I screen the offers
    Then the screening screened 2 offers, failed on 1 and left 1
