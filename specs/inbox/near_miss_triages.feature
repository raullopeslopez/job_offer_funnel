Feature: Near miss triages
  As a job seeker
  I want the language model to also mark the near misses OK or KO, saying why, and to tell me which rule to relax
  So that I see the false negatives my filters hide, and good offers stop being filtered out

  The triage (specs/inbox/offer_triages.feature) also takes the near misses: pending
  imported offers that are filtered, pass the title and fail exactly one rule of their
  reference profile (specs/inbox/filter_reasons.feature), have a description and have no
  verdict yet. They go after the pending offers that fit, in the same batches of up to
  5, from the most recently added, and the triager is told the same context. For each
  near miss it is also told the rule that filtered it and why.

  For a near miss, OK means a false negative: the rule filtered an offer worth my time.
  KO means it is rightly filtered. Either way it says why, in one sentence cut to 200
  characters. A near miss with a verdict stays filtered: rescuing it is promoting it
  (specs/inbox/rescues.feature) and marking it rightly filtered is a review, as always.
  Each triage also says how many near misses it marked OK.

  An OK near miss may carry a suggestion to relax the rule that filtered it, for its
  reference profile:
  - excluded: stop excluding the word that filtered it;
  - keywords: add a keyword, a word the triager gives that is in the offer's title or
    description;
  - work_mode: accept the work mode its reading says.
  Location and stable are not relaxed: the offer can only be rescued. A suggestion is
  kept only if it holds the rule for relaxing a criterion: against the imported offers,
  no offer I discarded would fit the profile with the change and does not fit it now.
  It says how many offers it would bring into Pending. Kept suggestions join the criteria suggestions
  (specs/inbox/criteria_suggestions.feature), marked as from the triager with its why and
  the offer it comes from, and are listed while they still hold the rule. Accepting one
  is a criteria change made from that offer (specs/inbox/criteria_changes.feature); "Not
  now" hides it for good, like any criteria suggestion. Nothing is applied on its own.

  Background:
    Given a job board named "Remote OK" imported from the feed "remoteok"
    And a search profile named "Backend" with:
      | titles            | Backend Engineer |
      | keywords          | Python           |
      | excluded_keywords | Senior           |
    And the job board "Remote OK" was imported with:
      | title                   | company | description               | url                    |
      | Backend Engineer        | Acme    | Python services.          | https://remoteok.com/1 |
      | Backend Engineer        | Globex  | Go services for payments. | https://remoteok.com/2 |
      | Senior Backend Engineer | Initech | Python platform.          | https://remoteok.com/3 |
      | Data Engineer           | Hooli   | Spark pipelines.          | https://remoteok.com/4 |

  # --- Which offers are triaged ---

  Scenario: The near misses go after the offers that fit, with the rule that filtered them
    When I triage the offers
    Then the offer triager was asked first about the offer of "Acme", then about those of "Globex" and "Initech"
    And it was told that "Globex" was filtered by "keywords" and "Initech" by "excluded"

  Scenario: A filtered offer that is not a near miss is not triaged
    When I triage the offers
    Then the offer triager was not asked about the offer of "Hooli"

  # --- Verdicts ---

  Scenario Outline: A near miss with a verdict stays filtered
    Given the offer triager says the offer of "Globex" is <verdict> because "<why>"
    When I triage the offers
    Then the offer of "Globex" has the verdict "<verdict>" because "<why>"
    And the offer of "Globex" is filtered

    Examples:
      | verdict | why                                       |
      | OK      | A backend role like the ones you promote. |
      | KO      | Go only, and you discard Go roles.        |

  Scenario: The triage says how many near misses it marked OK
    Given the offer triager says the offers of "Globex" and "Initech" are OK
    And the offer triager says the offer of "Acme" is KO because "Crypto."
    When I triage the offers
    Then the triage says 1 KO among the offers that fit and 2 OK among the near misses

  # --- Relaxing a rule ---

  Scenario Outline: An OK near miss suggests relaxing the rule that filtered it
    Given the offer triager says the offer of "<company>" is OK because "Worth it."<keyword>
    When I triage the offers
    Then the criteria suggestions include <change> in "Backend", from the triager because "Worth it."
    And it comes from the offer of "<company>"
    And it would bring 1 offer into Pending

    Examples:
      | company | keyword                             | change                        |
      | Initech |                                     | to stop excluding "Senior"    |
      | Globex  | , suggesting the keyword "payments" | to add the keyword "payments" |

  Scenario: An OK near miss filtered by its work mode suggests accepting that work mode
    Given a search profile named "Remote" with:
      | titles     | Platform Engineer |
      | work_modes | remote            |
    And the job board "Remote OK" was imported with:
      | title             | company | description               | url                    |
      | Platform Engineer | Wayne   | Hybrid, two days on site. | https://remoteok.com/5 |
    And the offer of "Wayne" was read as "hybrid" for the profile "Remote"
    And the offer triager says the offer of "Wayne" is OK because "Worth it."
    When I triage the offers
    Then the criteria suggestions include to accept the work mode "hybrid" in "Remote", from the triager because "Worth it."

  Scenario: A suggestion that would make an offer I discarded fit is not kept
    Given I discarded an imported offer as "Senior Backend Engineer" with the description "Python services."
    And the offer triager says the offer of "Initech" is OK because "Worth it."
    When I triage the offers
    Then the criteria suggestions include nothing from the offer of "Initech"

  Scenario Outline: A KO near miss, or a keyword that is not in the offer, suggests nothing
    Given the offer triager says the offer of "<company>" is <verdict>
    When I triage the offers
    Then the criteria suggestions include nothing from the offer of "<company>"

    Examples:
      | company | verdict                                               |
      | Initech | KO because "You discard senior roles."                |
      | Globex  | OK because "Worth it.", suggesting the keyword "Rust" |

  Scenario: "Not now" hides a suggestion to relax a rule
    Given the offer triager says the offer of "Initech" is OK because "Worth it."
    And I triaged the offers
    When I say "Not now" to the suggestion to stop excluding "Senior" in "Backend"
    Then the criteria suggestions include nothing from the offer of "Initech"

  Scenario: Accepting a suggestion is a criteria change made from that near miss
    Given the offer triager says the offer of "Initech" is OK because "Worth it."
    And I triaged the offers
    When I accept the suggestion carried by the offer of "Initech"
    Then the profile "Backend" has no excluded_keywords
    And the latest change came from the offer of "Initech"
    And the offer of "Initech" is not filtered
