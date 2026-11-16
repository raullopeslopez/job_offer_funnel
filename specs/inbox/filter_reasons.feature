Feature: Filter reasons
  As a job seeker
  I want every imported offer to say which rule of my profiles it passed and which one filtered it
  So that I can tell a badly written profile from an offer that rightly stays out

  A pending imported offer is filtered when it fits none of the search profiles
  (specs/inbox/filtered_offers.feature and specs/inbox/offer_readings.feature). Its filter
  reason gives the result of each rule against one profile, its reference profile: the
  one whose rules it fails the fewest times; on a tie, the first by name.
  Each rule passes, fails or is unknown, with what explains it:
  - title: the profile's title found in the offer's title;
  - keywords: the profile's keywords found in the title or the description, and those
    missing;
  - excluded: the excluded keyword found in the offer's title;
  - work_mode, location and stable: what the reading for the profile's location says,
    with its evidence; unknown when the offer has not been read or its reading does not
    say. The location rule fails, with the published location as evidence, when that
    location rules the offer out (specs/inbox/offer_readings.feature).
  Only the rules the profile asks for are listed: keywords, excluded, work_mode and
  location when the profile has some; title and stable always. Only a failed rule
  filters: an offer is filtered exactly when its reference profile has a failed rule. A
  near miss is a filtered offer whose title passes and that fails exactly one rule.
  The reason also says whether the offer has a description, so that an unknown rule can
  be told apart from an offer with nothing to read. Like filtering, the reason always
  follows the current profiles. Offers added by hand, discarded or promoted have no
  filter reason; without search profiles there is no reference profile and the reason
  fails on the title.

  Background:
    Given the time is 2026-03-10 09:00
    And a job board named "Remote OK" imported from the feed "remoteok"
    And a search profile named "Backend" with:
      | titles            | Backend Engineer, Python Developer |
      | keywords          | Python, Django                     |
      | excluded_keywords | Senior, Lead                       |

  # --- The rules ---

  Scenario Outline: Each word rule says what explains its result
    Given the job board "Remote OK" was imported with:
      | title   | company | description   | url                    |
      | <title> | Acme    | <description> | https://remoteok.com/1 |
    When I view the offer "<title>"
    Then the filter reason is against the profile "Backend" with:
      | rule     | result         | found            | missing       |
      | title    | <title_result> | <title_found>    |               |
      | keywords | <kw_result>    | <kw_found>       | <kw_missing>  |
      | excluded | <ex_result>    | <ex_found>       |               |
      | stable   | unknown        |                  |               |

    Examples:
      | title                   | description       | title_result | title_found      | kw_result | kw_found       | kw_missing     | ex_result | ex_found |
      | Backend Engineer        | Python and Django | passed       | Backend Engineer | passed    | Python, Django |                | passed    |          |
      | Backend Engineer        | Python services   | passed       | Backend Engineer | failed    | Python         | Django         | passed    |          |
      | Senior Python Developer | Python and Django | passed       | Python Developer | passed    | Python, Django |                | failed    | Senior   |
      | Data Engineer           | Go services       | failed       |                  | failed    |                | Python, Django | passed    |          |

  Scenario Outline: The reading rules say what the reading says, with its evidence
    Given I delete the profile "Backend"
    And a search profile named "Remote in Spain" with:
      | titles     | Backend Engineer |
      | location   | Spain            |
      | work_modes | remote           |
    And the job board "Remote OK" was imported with:
      | title            | company | description   | url                    |
      | Backend Engineer | Acme    | <description> | https://remoteok.com/1 |
    And the offer reader answers for "Backend Engineer":
      | work_mode   | work_mode_evidence   | admits_location | admits_location_evidence | stable   | stable_evidence   |
      | <work_mode> | <work_mode_evidence> | <admits>        | <admits_evidence>        | <stable> | <stable_evidence> |
    And I read the offers
    When I view the offer "Backend Engineer"
    Then the filter reason is against the profile "Remote in Spain" with:
      | rule      | result          | value       | evidence             |
      | title     | passed          |             |                      |
      | work_mode | <mode_result>   | <work_mode> | <work_mode_evidence> |
      | location  | <loc_result>    | <admits>    | <admits_evidence>    |
      | stable    | <stable_result> | <stable>    | <stable_evidence>    |

    Examples:
      | description                                     | work_mode | work_mode_evidence         | admits | admits_evidence               | stable | stable_evidence    | mode_result | loc_result | stable_result |
      | Fully remote. Hiring across Europe. Full-time.  | remote    | Fully remote               | yes    | Hiring across Europe          | yes    | Full-time          | passed      | passed     | passed        |
      | Fully remote, anywhere in the United States.    | remote    | Fully remote               | no     | anywhere in the United States |        |                    | passed      | failed     | unknown       |
      | Based in our London office. Six-month contract. | onsite    | Based in our London office |        |                               | no     | Six-month contract | failed      | unknown    | failed        |

  Scenario: The reading rules are unknown until the offer is read
    Given I delete the profile "Backend"
    And a search profile named "Remote in Spain" with:
      | titles     | Backend Engineer |
      | location   | Spain            |
      | work_modes | remote           |
    And the job board "Remote OK" was imported with:
      | title            | company | description                 | url                    |
      | Backend Engineer | Acme    | Based in our London office. | https://remoteok.com/1 |
    When I view the offer "Backend Engineer"
    Then the filter reason is against the profile "Remote in Spain" with:
      | rule      | result  |
      | title     | passed  |
      | work_mode | unknown |
      | location  | unknown |
      | stable    | unknown |
    And the filter reason says the offer has a description

  Scenario: An imported offer without a description says so
    Given the job board "Remote OK" was imported with:
      | title            | company | description | url                    |
      | Backend Engineer | Acme    |             | https://remoteok.com/1 |
    When I view the offer "Backend Engineer"
    Then the filter reason says the offer has no description

  # --- The reference profile ---

  Scenario: The reference profile is the one whose rules the offer fails the fewest times
    Given a search profile named "Data" with:
      | titles   | Data Engineer |
      | keywords | Spark         |
    And the job board "Remote OK" was imported with:
      | title         | company | description      | url                    |
      | Data Engineer | Acme    | Python pipelines | https://remoteok.com/1 |
    When I view the offer "Data Engineer"
    Then the filter reason is against the profile "Data"

  Scenario: On a tie the reference profile is the first by name
    Given a search profile named "Analytics" with:
      | titles | Analytics Engineer |
    And the job board "Remote OK" was imported with:
      | title         | company | description       | url                    |
      | Data Engineer | Acme    | Python and Django | https://remoteok.com/1 |
    When I view the offer "Data Engineer"
    Then the filter reason is against the profile "Analytics"

  Scenario: An offer that fits a profile has it as its reference profile
    Given a search profile named "Python" with:
      | titles | Backend Engineer |
    And the job board "Remote OK" was imported with:
      | title            | company | description     | url                    |
      | Backend Engineer | Acme    | Python services | https://remoteok.com/1 |
    When I view the offer "Backend Engineer"
    Then the filter reason is against the profile "Python"
    And the offer is not filtered

  Scenario: The reason follows the current profiles
    Given the job board "Remote OK" was imported with:
      | title            | company | description     | url                    |
      | Backend Engineer | Acme    | Python services | https://remoteok.com/1 |
    And I edit the profile "Backend" to have the keywords "Python"
    When I view the offer "Backend Engineer"
    Then the filter reason is against the profile "Backend" with:
      | rule     | result  | found            | missing |
      | title    | passed  | Backend Engineer |         |
      | keywords | passed  | Python           |         |
      | excluded | passed  |                  |         |
      | stable   | unknown |                  |         |

  # --- Near misses ---

  Scenario Outline: A near miss passes the title and fails a single rule
    Given the job board "Remote OK" was imported with:
      | title   | company | description   | url                    |
      | <title> | Acme    | <description> | https://remoteok.com/1 |
    When I view the offer "<title>"
    Then the offer is <filtered>
    And the offer is <near_miss>

    Examples:
      | title                   | description       | filtered     | near_miss       |
      | Backend Engineer        | Python and Django | not filtered | not a near miss |
      | Backend Engineer        | Python services   | filtered     | a near miss     |
      | Senior Backend Engineer | Python services   | filtered     | not a near miss |
      | Data Engineer           | Python and Django | filtered     | not a near miss |

  # --- The reason agrees with filtering ---

  Scenario Outline: An offer is filtered exactly when its reference profile has a failed rule
    Given the job board "Remote OK" was imported with:
      | title   | company | description   | url                    |
      | <title> | Acme    | <description> | https://remoteok.com/1 |
    When I view the offer "<title>"
    Then the offer is <filtered>
    And the filter reason has <failed> failed rules

    Examples:
      | title                     | description               | filtered     | failed |
      | Backend Engineer          | Python and Django         | not filtered | 0      |
      | backend engineer (Remote) | We love python and django | not filtered | 0      |
      | Backend Engineer          | Go services               | filtered     | 1      |
      | Senior Backend Engineer   | Python services           | filtered     | 2      |
      | Data Engineer             | Go services               | filtered     | 2      |

  # --- Offers without a reason ---

  Scenario: Without search profiles the reason fails on the title
    Given there are no search profiles
    And the job board "Remote OK" was imported with:
      | title            | company | description     | url                    |
      | Backend Engineer | Acme    | Python services | https://remoteok.com/1 |
    When I view the offer "Backend Engineer"
    Then the filter reason has no reference profile and fails on the title
    And the offer is not a near miss

  Scenario Outline: Only pending imported offers have a filter reason
    Given the job board "Remote OK" was imported with:
      | title         | company | description     | url                    |
      | Data Engineer | Globex  | Spark pipelines | https://remoteok.com/1 |
    And an offer for "Initech" as "Frontend Engineer"
    And I discarded the offer "Data Engineer"
    When I view the offer "<title>"
    Then the offer has no filter reason

    Examples:
      | title             |
      | Data Engineer     |
      | Frontend Engineer |

  # --- Listing ---

  Scenario Outline: List the filtered offers that are near misses or fail a rule
    Given the job board "Remote OK" was imported with:
      | title                   | company  | description       | url                    |
      | Backend Engineer        | Acme     | Python and Django | https://remoteok.com/1 |
      | Backend Engineer        | Globex   | Python services   | https://remoteok.com/2 |
      | Senior Backend Engineer | Initech  | Python services   | https://remoteok.com/3 |
      | Data Engineer           | Umbrella | Go services       | https://remoteok.com/4 |
    When I list the pending offers that are <filter>
    Then the offers are, in order, from: <companies>

    Examples:
      | filter                      | companies                       |
      | near misses                 | "Globex"                        |
      | failing the rule "keywords" | "Umbrella", "Initech", "Globex" |
      | failing the rule "excluded" | "Initech"                       |
      | failing the rule "title"    | "Umbrella"                      |

  Scenario: Count the filtered offers by failed rule
    Given the job board "Remote OK" was imported with:
      | title                   | company  | description       | url                    |
      | Backend Engineer        | Acme     | Python and Django | https://remoteok.com/1 |
      | Backend Engineer        | Globex   | Python services   | https://remoteok.com/2 |
      | Senior Backend Engineer | Initech  | Python services   | https://remoteok.com/3 |
      | Data Engineer           | Umbrella | Go services       | https://remoteok.com/4 |
    When I count the filtered offers by failed rule
    Then the counts are 3 filtered, of them 1 near misses, failing:
      | rule     | offers |
      | title    | 1      |
      | keywords | 3      |
      | excluded | 1      |

  # --- Errors ---

  Scenario: Listing by an unknown rule is rejected
    When I list the pending offers that are failing the rule "salary"
    Then it is rejected as invalid
