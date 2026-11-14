Feature: Offer triages
  As a job seeker
  I want a language model to compare each pending offer, description included, with what I decided before
  So that the offers I would discard are pointed out to me, while I keep the last word

  A triage sends the offer triager, in a single request, up to 5 pending imported offers
  that fit a search profile, have a description and were not triaged yet, from the most
  recently added: their title, company and description. With them, once, it is told:
  - the search profiles: name, titles, keywords and excluded keywords;
  - my last 30 promoted and last 30 discarded imported offers, from the most recent: their
    title and, for the discarded ones, the discard reason and its word;
  - its own mistakes, the last 20 of each, from the most recent: the rejected suggestions
    (offers with a suggested discard that I promoted) and the missed discards (offers
    triaged without a suggested discard that I discarded), with their title and, for the
    rejected ones, the suggested reason.
  Expired offers are not decisions and are never told.
  For each offer the triager answers with nothing to say, or with a suggested discard: a
  reason of the list (title_word, stack, location, contract or company) and its evidence.
  For title_word the evidence is the word, which must be a word of the title; for the
  other reasons it is a sentence of the description, letter for letter. Any other answer
  is not kept. Either way the offer is triaged and is not triaged again. An offer the
  triager does not answer for, or a request it fails, leaves the offers to be triaged again.
  A suggested discard is never applied on its own: the offer stays pending, and discarding
  it with that reason and word is a normal discard (specs/inbox/inbox.feature). How well
  the triager does is part of the offer quality (specs/inbox/offer_quality.feature).
  Without an offer triager the app offers no triage and works as always.

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
    Given the offer triager answers for the offer of "<company>" with the reason "<reason>" and the evidence "<evidence>"
    When I triage the offers
    Then the offer of "<company>" has a suggested discard because "<reason>" with "<evidence>"
    And the offer of "<company>" is "pending"

    Examples:
      | company | reason     | evidence                   |
      | Globex  | contract   | Part-time, 20 hours a week |
      | Acme    | company    | for a crypto exchange      |
      | Initech | title_word | lead                       |

  Scenario Outline: An answer without its evidence is not kept
    Given the offer triager answers for the offer of "<company>" with the reason "<reason>" and the evidence "<evidence>"
    When I triage the offers
    Then the offer of "<company>" has no suggested discard
    And the triage triaged 3 offers, failed on 0 and left 0

    Examples:
      | company | reason     | evidence  |
      | Globex  | contract   | Full-time |
      | Globex  | title_word | Senior    |
      | Initech | title_word | Lea       |
      | Initech | title_word | Python    |
      | Acme    | none       | crypto    |
      | Acme    | expired    | crypto    |

  Scenario: An offer the triager has nothing to say about has no suggested discard
    When I triage the offers
    Then the offer of "Acme" has no suggested discard
    And the triage triaged 3 offers, failed on 0 and left 0

  # --- Which offers are triaged ---

  Scenario: The pending imported offers that fit and were not triaged yet go in a single request
    Given an offer for "Umbrella" as "Backend Engineer"
    And I discarded the offer of "Initech"
    When I triage the offers
    Then the offer triager was asked once, only about the offers of "Acme" and "Globex"

  Scenario: An offer is triaged once
    Given I triaged the offers
    When I triage the offers
    Then the triage triaged 0 offers, failed on 0 and left 0

  Scenario: At most 5 offers are triaged at a time
    Given the job board "Remote OK" was imported with 4 more offers as "Backend Engineer"
    When I triage the offers
    Then the triage triaged 5 offers, failed on 0 and left 2

  # --- What the triager is told ---

  Scenario: The triager is told the profiles and my decisions, not the expired ones
    Given I promoted the offer of "Initech"
    And I discarded the offer of "Hooli" because "stack"
    And the job board "Remote OK" was imported again without the offer of "Globex"
    When I triage the offers
    Then the offer triager was told the profile "Backend" and these decisions:
      | title                 | decision  | reason | word |
      | Backend Engineer Lead | promoted  |        |      |
      | Data Engineer         | discarded | stack  |      |

  Scenario: The triager is told its own mistakes
    Given the offer triager answers for the offer of "Globex" with the reason "contract" and the evidence "Part-time, 20 hours a week"
    And I triaged the offers
    And I promoted the offer of "Globex"
    And I discarded the offer of "Acme" because "company"
    And I promoted the offer of "Initech"
    And the job board "Remote OK" was imported with:
      | title            | company | description    | url                    |
      | Backend Engineer | Wayne   | Rust services. | https://remoteok.com/5 |
    When I triage the offers
    Then the offer triager was told these mistakes:
      | title            | mistake             | reason   |
      | Backend Engineer | rejected suggestion | contract |
      | Backend Engineer | missed discard      |          |

  # --- Without a triager, and when it fails ---

  Scenario Outline: The triage is offered only with an offer triager
    Given the offer triager is <triager>
    When I check whether the triage is available
    Then it is <availability>

    Examples:
      | triager    | availability  |
      | configured | available     |
      | missing    | not available |

  Scenario: Cannot triage without an offer triager
    Given the offer triager is missing
    When I triage the offers
    Then it is rejected because the offer triager is not available
    And the offer of "Acme" has no suggested discard

  Scenario: An offer the triager does not answer for is left to be triaged again
    Given the offer triager does not answer for the offer of "Globex"
    When I triage the offers
    Then the triage triaged 2 offers, failed on 1 and left 1

  Scenario: A request the triager fails leaves every offer to be triaged again
    Given the offer triager fails
    When I triage the offers
    Then the triage triaged 0 offers, failed on 3 and left 3
