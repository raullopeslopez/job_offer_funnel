Feature: Near miss triages
  As a job seeker
  I want the language model to also mark the near misses OK or KO, saying why, and to tell me which rule to relax
  So that I see the false negatives my filters hide, and good offers stop being filtered out

  The triage (specs/inbox/offer_triages.feature) also takes the near misses: pending
  imported offers that are filtered, pass the title and fail exactly one rule of their
  reference profile (specs/inbox/filter_reasons.feature), have a description and have no
  verdict yet. They go after the pending offers that fit, in the same batches (up to 5
  with Groq, 20 with Claude Code), from the most recently added, and the triager is told
  the same context, with the location each profile asks for and the location each offer
  is published in. For each near miss it is also told the rule that filtered it and why,
  and it is asked to judge that rule, not the role: the title already fits.

  For a near miss, OK means a false negative: the rule that filtered it is wrong for this
  offer. KO means it is rightly filtered. Either way it says why yes and why not, with their
  quotes, and its confidence, as for any offer. An OK must quote, letter for letter, a
  sentence of at least four words of its description that rebuts the rule (for the location rule, one that says
  it can be done from the profile's location); a quote of its title or its published
  location does not. An OK without such a quote is kept as KO, with the triager's whys:
  rightly filtered, and it suggests nothing.
  A near miss with a verdict stays filtered: rescuing it is promoting it
  (specs/inbox/rescues.feature) and marking it rightly filtered is a review, as always.
  Each triage also says how many near misses it marked OK.

  An OK near miss may carry a suggestion to relax the rule that filtered it, for its
  reference profile:
  - excluded: stop excluding the word that filtered it;
  - keywords: stop asking for the keywords it lacks (a profile asks for all of them);
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

  Scenario: The triager is told the location a near miss is published in
    Given a search profile named "Spain" with:
      | titles   | Platform Engineer |
      | location | Spain             |
    And the job board "Remote OK" was imported with:
      | title             | company | description          | url                    | location |
      | Platform Engineer | Wayne   | Kubernetes platform. | https://remoteok.com/5 | USA      |
    When I triage the offers
    Then it was told that "Wayne" was filtered by "location" and is published in "USA"

  Scenario: A filtered offer that is not a near miss is not triaged
    When I triage the offers
    Then the offer triager was not asked about the offer of "Hooli"

  # --- Verdicts ---

  Scenario Outline: A near miss with a verdict stays filtered
    Given the offer triager says the offer of "Globex" is <verdict> because "<why>", quoting "Go services for payments."
    When I triage the offers
    Then the offer of "Globex" has the verdict "<verdict>" because "<why>"
    And the offer of "Globex" is filtered

    Examples:
      | verdict | why                                          |
      | OK      | Payments backend: Python is not a must here. |
      | KO      | Go only, and you discard Go roles.           |

  Scenario Outline: An OK near miss without a quote of four words of its description is kept as KO
    Given the offer triager says the offer of "Globex" is OK because "Backend services and APIs.", quoting "<quote>"
    When I triage the offers
    Then the offer of "Globex" has the verdict "KO"
    And the criteria suggestions include nothing from the offer of "Globex"

    Examples:
      | quote                    |
      | Backend Engineer         |
      | Fully remote from Spain. |
      | Go services              |

  Scenario: An OK near miss with no quote is kept as KO
    Given the offer triager says the offer of "Globex" is OK because "Backend services and APIs."
    When I triage the offers
    Then the offer of "Globex" has the verdict "KO"

  Scenario Outline: A near miss filtered by its location is OK only with a quote that rebuts it
    Given a search profile named "Spain" with:
      | titles   | Platform Engineer |
      | location | Spain             |
    And the job board "Remote OK" was imported with:
      | title             | company | description                                   | url                    | location |
      | Platform Engineer | Wayne   | Remote from the US or Europe, Spain included. | https://remoteok.com/5 | USA      |
    And the offer triager says the offer of "Wayne" is OK because "<why>", quoting "<quote>"
    When I triage the offers
    Then the offer of "Wayne" has the verdict "<verdict>"
    And the offer of "Wayne" is filtered

    Examples:
      | why                          | quote                                         | verdict |
      | Open to Spain.               | Remote from the US or Europe, Spain included. | OK      |
      | Java microservices and APIs. | USA                                           | KO      |
      | Remote.                      | Remote                                        | KO      |

  Scenario: The triage says how many near misses it marked OK
    Given the offer triager says the offers of "Globex" and "Initech" are OK, quoting their descriptions
    And the offer triager says the offer of "Acme" is KO because "Crypto."
    When I triage the offers
    Then the triage says 1 KO among the offers that fit and 2 OK among the near misses

  # --- Relaxing a rule ---

  Scenario Outline: An OK near miss suggests relaxing the rule that filtered it
    Given the offer triager says the offer of "<company>" is OK because "Worth it.", quoting "<quote>"
    When I triage the offers
    Then the criteria suggestions include <change> in "Backend", from the triager because "Worth it."
    And it comes from the offer of "<company>"
    And it would bring 1 offer into Pending

    Examples:
      | company | quote                     | change                                  |
      | Initech | Python platform.          | to stop excluding "Senior"              |
      | Globex  | Go services for payments. | to stop asking for the keyword "Python" |

  Scenario: An OK near miss filtered by its work mode suggests accepting that work mode
    Given a search profile named "Remote" with:
      | titles     | Platform Engineer |
      | work_modes | remote            |
    And the offer reader reads the offer of "Wayne" as "hybrid"
    And the job board "Remote OK" was imported with:
      | title             | company | description               | url                    |
      | Platform Engineer | Wayne   | Hybrid, two days on site. | https://remoteok.com/5 |
    And the offer triager says the offer of "Wayne" is OK because "Worth it.", quoting "Hybrid, two days on site."
    When I triage the offers
    Then the criteria suggestions include to accept the work mode "hybrid" in "Remote", from the triager because "Worth it."

  Scenario: A suggestion that would make an offer I discarded fit is not kept
    Given I discarded an imported offer as "Senior Backend Engineer" with the description "Python services."
    And the offer triager says the offer of "Initech" is OK because "Worth it.", quoting "Python platform."
    When I triage the offers
    Then the criteria suggestions include nothing from the offer of "Initech"

  Scenario: A KO near miss suggests nothing
    Given the offer triager says the offer of "Initech" is KO because "You discard senior roles."
    When I triage the offers
    Then the criteria suggestions include nothing from the offer of "Initech"

  Scenario: "Not now" hides a suggestion to relax a rule
    Given the offer triager says the offer of "Initech" is OK because "Worth it.", quoting "Python platform."
    And I triaged the offers
    When I say "Not now" to the suggestion to stop excluding "Senior" in "Backend"
    Then the criteria suggestions include nothing from the offer of "Initech"

  Scenario: Accepting a suggestion is a criteria change made from that near miss
    Given the offer triager says the offer of "Initech" is OK because "Worth it.", quoting "Python platform."
    And I triaged the offers
    When I accept the suggestion carried by the offer of "Initech"
    Then the profile "Backend" has no excluded_keywords
    And the latest change came from the offer of "Initech"
    And the offer of "Initech" is not filtered
