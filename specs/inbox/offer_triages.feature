Feature: Offer triages
  As a job seeker
  I want a language model to tell me, for each pending offer, whether it fits what I decided before and why, and what to change in my criteria
  So that I see what it thinks of every offer, and each batch that reaches Pending is better than the last, while I keep the last word

  A triage sends the offer triager, in a single request, up to 5 pending imported offers
  that fit a search profile, have a description and have no verdict yet, from the most
  recently added: their title, company and description. With them, once, it is told:
  - the search profiles: name, titles, keywords and excluded keywords;
  - my last 30 promoted and last 30 discarded imported offers, from the most recent: their
    title and, for the discarded ones, the discard reason and its word;
  - its own mistakes, the last 20 of each, from the most recent: the rejected suggestions
    (offers with a suggested discard that I promoted) and the missed discards (offers
    that it said fit and that I discarded), with their title and, for the rejected ones,
    the suggested reason.
  Expired offers are not decisions and are never told.

  For each offer the triager answers with a verdict, "fits" or "does not fit", and why:
  one sentence in its own words, cut to 200 characters. When it does not fit, it adds a
  reason of the list (title_word, stack, location, contract or company) and its evidence.
  For title_word the evidence is the word, which must be a word of the title; for the
  other reasons it is a sentence of the description, letter for letter. Only then is it
  a suggested discard; a "does not fit" without its evidence keeps its verdict and why,
  and has no suggested discard. Either way the offer has a verdict and is not triaged
  again. An offer the triager does not answer for, or a request it fails, leaves the
  offers to be triaged again. Each triage says how many offers it triaged, how many fit,
  how many do not, how many failed and how many are left.

  With the batch, the triager may suggest excluding a word from a search profile, with
  why. A suggestion is kept only if it holds the rule for changing a criterion: against
  the imported offers, excluding it would have filtered no offer I promoted and at least
  one I discarded (specs/inbox/criteria_previews.feature). It must also be a word the
  profile does not exclude yet and that is not part of its titles or keywords, and not
  one I said "Not now" to. Kept suggestions join the criteria suggestions
  (specs/inbox/criteria_suggestions.feature), marked as from the triager with its why,
  and are listed while they still hold the rule.

  Nothing is ever applied on its own: the offer stays pending, discarding it with the
  suggested reason and word is a normal discard (specs/inbox/inbox.feature), and
  accepting a suggestion is a criteria change (specs/inbox/criteria_changes.feature). How
  well the triager does is part of the offer quality (specs/inbox/offer_quality.feature).
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

  # --- Verdicts ---

  Scenario Outline: Every triaged offer has a verdict and why, and stays pending
    Given the offer triager says the offer of "Acme" <verdict> because "<why>"
    When I triage the offers
    Then the offer of "Acme" has the verdict "<verdict>" because "<why>"
    And the offer of "Acme" is "pending"

    Examples:
      | verdict      | why                                             |
      | fits         | Python backend role like the ones you promoted. |
      | does not fit | The company works on crypto, which you discard. |

  Scenario: The triage says how many offers fit and how many do not
    Given the offer triager says the offer of "Acme" does not fit because "Crypto."
    And the offer triager says the offers of "Globex" and "Initech" fit
    When I triage the offers
    Then the triage triaged 3 offers, failed on 0 and left 0
    And the triage says 2 fit and 1 does not

  Scenario: A why longer than 200 characters is cut
    Given the offer triager says the offer of "Acme" fits with a why of 250 characters
    When I triage the offers
    Then the offer of "Acme" has a why of 200 characters

  # --- Suggested discards ---

  Scenario Outline: A "does not fit" with its evidence is a suggested discard
    Given the offer triager says the offer of "<company>" does not fit, with the reason "<reason>" and the evidence "<evidence>"
    When I triage the offers
    Then the offer of "<company>" has a suggested discard because "<reason>" with "<evidence>"
    And the offer of "<company>" is "pending"

    Examples:
      | company | reason     | evidence                   |
      | Globex  | contract   | Part-time, 20 hours a week |
      | Acme    | company    | for a crypto exchange      |
      | Initech | title_word | lead                       |

  Scenario Outline: A "does not fit" without its evidence keeps its verdict, with no suggested discard
    Given the offer triager says the offer of "<company>" does not fit, with the reason "<reason>" and the evidence "<evidence>"
    When I triage the offers
    Then the offer of "<company>" has the verdict "does not fit"
    And the offer of "<company>" has no suggested discard
    And the triage triaged 3 offers, failed on 0 and left 0

    Examples:
      | company | reason     | evidence  |
      | Globex  | contract   | Full-time |
      | Globex  | title_word | Senior    |
      | Initech | title_word | Lea       |
      | Initech | title_word | Python    |
      | Acme    | none       | crypto    |
      | Acme    | expired    | crypto    |

  Scenario: An offer that fits has no suggested discard
    Given the offer triager says the offer of "Acme" fits, with the reason "company" and the evidence "for a crypto exchange"
    When I triage the offers
    Then the offer of "Acme" has the verdict "fits"
    And the offer of "Acme" has no suggested discard

  # --- Suggested criteria changes ---

  Scenario: A suggestion that filters a discarded offer and no promoted one is kept
    Given I discarded the offer of "Initech" because "title_word" with the word "Lead"
    And the offer triager suggests excluding "Lead" from "Backend" because "You discard lead roles."
    When I triage the offers
    Then the criteria suggestions include excluding "Lead" from "Backend", from the triager because "You discard lead roles."

  Scenario Outline: A suggestion that does not hold the rule is not kept
    Given I discarded the offer of "Initech" because "company"
    And <state>
    And the offer triager suggests excluding "<word>" from "<profile>" because "Noise."
    When I triage the offers
    Then the criteria suggestions do not include excluding "<word>" from "<profile>"

    Examples: it would filter an offer I promoted, none I discarded, or it is not a new word
      | state                                                     | word     | profile |
      | I promoted an imported offer as "Lead Backend Engineer"   | Lead     | Backend |
      | I discarded the offer of "Hooli" because "stack"          | Spark    | Backend |
      | the profile "Backend" has the keywords "Platform"         | Platform | Backend |
      | the profile "Backend" excludes "lead"                     | Lead     | Backend |
      | I said "Not now" to excluding "Lead" from "Backend"       | Lead     | Backend |
      | no search profile named "Data"                            | Lead     | Data    |

  Scenario: A kept suggestion that no longer holds the rule is no longer listed
    Given I discarded the offer of "Initech" because "title_word" with the word "Lead"
    And the offer triager suggests excluding "Lead" from "Backend" because "You discard lead roles."
    And I triaged the offers
    And the job board "Remote OK" was imported with:
      | title                 | company | description      | url                    |
      | Lead Backend Engineer | Wayne   | Python services. | https://remoteok.com/5 |
    And I promoted the offer of "Wayne"
    When I list the suggestions
    Then the criteria suggestions do not include excluding "Lead" from "Backend"

  # --- Which offers are triaged ---

  Scenario: The pending imported offers that fit and have no verdict yet go in a single request
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
    Given the offer triager says the offer of "Globex" does not fit, with the reason "contract" and the evidence "Part-time, 20 hours a week"
    And the offer triager says the offer of "Acme" fits
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
    And the offer of "Acme" has no verdict

  Scenario: An offer the triager does not answer for is left to be triaged again
    Given the offer triager does not answer for the offer of "Globex"
    When I triage the offers
    Then the triage triaged 2 offers, failed on 1 and left 1

  Scenario: A request the triager fails leaves every offer to be triaged again
    Given the offer triager fails
    When I triage the offers
    Then the triage triaged 0 offers, failed on 3 and left 3
