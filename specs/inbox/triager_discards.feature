Feature: Triager discards
  As a job seeker
  I want to let the offer triager discard, when I ask it to, the pending offers it is sure are false positives
  So that the noise leaves Pending without a click per offer, while I see which discards are its own and can take any of them back

  The offer triager (specs/inbox/offer_triages.feature) marks offers KO, but nothing it
  says is applied on its own. When I ask it, the triager discards the pending offers it
  marked KO with high confidence: imported offers that fit a search profile now (not the
  filtered ones, near misses included) and that it has not discarded before. Each one is
  discarded with the reason and word of its suggested discard, or with "none" when it
  has none. It says how many it discarded and which ones. Asking it needs no offer
  triager: it uses the verdicts already given. How many it would discard can be seen
  before asking.

  A triager discard is a discard (specs/inbox/inbox.feature), marked as the triager's.
  Restoring it is restoring any discard: the offer is pending again, and it stays marked
  as restored, so the triager never discards it again. A restored offer that I discard
  myself is my discard.

  A triager discard is not my decision, and not restoring one does not make it mine: it
  never counts as an offer I discarded. Not in my precision nor the triager's
  (specs/inbox/offer_quality.feature), which say apart how many it discarded and how
  many I restored; not in the rule for changing a criterion
  (specs/inbox/criteria_previews.feature) nor in the criteria suggestions; and never in
  what the triager is told as my decisions.

  Background:
    Given a job board named "Remote OK" imported from the feed "remoteok"
    And a search profile named "Backend" with:
      | titles   | Backend Engineer |
      | keywords | Python           |
    And the job board "Remote OK" was imported with:
      | title                 | company | description                            | url                    |
      | Backend Engineer      | Acme    | Python services for a crypto exchange. | https://remoteok.com/1 |
      | Backend Engineer      | Globex  | Python services. Part-time.            | https://remoteok.com/2 |
      | Backend Engineer Lead | Initech | Python platform.                       | https://remoteok.com/3 |
      | Backend Engineer      | Hooli   | Go pipelines.                          | https://remoteok.com/4 |

  # --- Which offers ---

  Scenario: The triager discards the fitting pending offers it marked KO with high confidence
    Given these verdicts:
      | company | verdict | confidence | suggested discard |
      | Acme    | KO      | high       | company           |
      | Globex  | KO      | medium     | contract          |
      | Initech | OK      | high       |                   |
      | Hooli   | KO      | high       |                   |
    When I let the triager discard
    Then the triager discarded 1 offer: the offer of "Acme"
    And the offer of "Acme" is "discarded" by the triager
    And the offer of "Globex" is "pending"
    And the offer of "Initech" is "pending"
    And the offer of "Hooli" is "pending"

  Scenario: How many it would discard is seen before asking
    Given these verdicts:
      | company | verdict | confidence | suggested discard |
      | Acme    | KO      | high       | company           |
      | Globex  | KO      | high       |                   |
      | Initech | KO      | low        |                   |
    When I check whether the triage is available
    Then the triager would discard 2 offers

  Scenario Outline: It discards with the reason and word of its suggested discard, or none
    Given the offer of "Initech" has the verdict KO with high confidence<suggested>
    When I let the triager discard
    Then the offer of "Initech" is "discarded" by the triager with reason "<reason>" and <word>

    Examples:
      | suggested                                                          | reason     | word        |
      | , with a suggested discard because "title_word" with "Lead"        | title_word | word "Lead" |
      | , with a suggested discard because "stack" with "Python platform." | stack      | no word     |
      |                                                                    | none       | no word     |

  Scenario: It asks nothing of the offer triager
    Given the offer of "Acme" has the verdict KO with high confidence
    And the offer triager is missing
    When I let the triager discard
    Then the offer of "Acme" is "discarded" by the triager

  Scenario: With nothing to discard it discards nothing
    Given the offer of "Acme" has the verdict KO with medium confidence
    When I let the triager discard
    Then the triager discarded 0 offers

  # --- Taking it back ---

  Scenario: Restoring a triager discard makes it pending again, and the triager never discards it again
    Given the offer of "Acme" has the verdict KO with high confidence
    And I let the triager discard
    And I restored the offer of "Acme"
    When I let the triager discard
    Then the triager discarded 0 offers
    And the offer of "Acme" is "pending", restored from a triager discard

  Scenario: A restored offer that I discard is my discard
    Given the offer of "Acme" has the verdict KO with high confidence
    And I let the triager discard
    And I restored the offer of "Acme"
    When I discard the offer of "Acme" because "company"
    Then the offer of "Acme" is "discarded" by me

  Scenario: An offer I discard is my discard
    Given the offer of "Acme" has the verdict KO with high confidence
    When I discard the offer of "Acme" because "company"
    Then the offer of "Acme" is "discarded" by me

  # --- Never my decision ---

  Scenario: A triager discard is never told to the triager as my decision
    Given the offer of "Acme" has the verdict KO with high confidence
    And I let the triager discard
    And I discarded the offer of "Initech" because "title_word" with the word "Lead"
    When I triage the offers
    Then the offer triager was told the profile "Backend" and these decisions:
      | title                 | decision  | reason     | word |
      | Backend Engineer Lead | discarded | title_word | Lead |

  Scenario: A triager discard does not hold the rule for changing a criterion
    Given the offer of "Acme" has the verdict KO with high confidence
    And I let the triager discard
    When I preview the profile "Backend" with the excluded_keywords "crypto"
    Then the change would have filtered 0 offers I promoted and 0 I discarded
