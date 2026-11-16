Feature: Offer readings
  As a job seeker
  I want the app to read what each offer says about remote work and where I can live
  So that offers I cannot take are filtered even when their title fits

  A title says little: "Backend Engineer" may be remote from anywhere or three days a
  week in an office. Reading the offers sends the title, the location its source
  publishes (specs/inbox/offer_countries.feature) and the description of each pending
  imported offer to the offer reader, which answers three things:
  - its work mode: remote, hybrid or onsite;
  - whether the job can be done living in a location: yes or no;
  - whether it is a stable job: yes for a full-time position with no end date, as an
    employee or as a contractor; no when it is paid by the task or by the hour,
    temporary or part-time.
  Each answer comes with its evidence, the words of the title, the location or the
  description that say so. An answer whose evidence is in none of them, letter for
  letter, is not kept. What none of them says stays unknown.
  Where the company is does not matter; where I can live does. A remote job whose title
  or location names a place, such as "Backend Engineer - UK", "US Remote" or "USA only",
  can only be done living there, unless the description opens it to other places.
  An offer is read once for each location of the search profiles it fits by its title,
  keywords and exclusions (specs/inbox/filtered_offers.feature); for profiles without a
  location it is read without that question. Offers without a description (added by
  hand or from an email alert) are never read. A pending offer that gets its location
  after it was read (an offer imported before locations were kept,
  specs/inbox/offer_countries.feature) loses its readings and is read again with it; an
  offer that is no longer pending keeps them.
  There are two offer readers, and the app is set up with one, as with the offer
  triagers (specs/inbox/offer_triages.feature): Groq (the default, and the one of the
  deployed app) or Claude Code on my Claude subscription, which only runs on my computer
  where Claude Code is installed and signed in. Both are told the same and answer the
  same, and what they say is kept and filters the same way. So that each reader's limits
  are respected, Groq reads up to 5 offers at a time and Claude Code up to 20, in a
  single request.
  A reading adds three rules to fitting a profile, and only what is known can filter:
  - the offer's work mode, when known, is one of the profile's work modes, if it has any;
  - the offer, when known, can be done living in the profile's location, if it has one;
  - the offer, when known, is a stable job, whatever the profile.
  So an offer that has not been read, or whose description says nothing, is never
  filtered for it. Whether an offer is filtered still follows the current profiles.
  The location its source publishes can also rule an offer out, without reading it. When
  every part of that location (between commas, "/", "|", ";", " or " and " and ") is a
  known country (specs/inbox/offer_countries.feature) and none of them is a country the
  profile's location names, the offer cannot be done living there: its location rule
  fails, with the published location as evidence, whatever its reading says, and it is
  not read for that location. "Worldwide", "Anywhere", a region ("Europe", "EMEA") or any
  other text in the location leaves the question to the reading.

  Background:
    Given the time is 2026-03-10 09:00
    And a job board named "Remote OK" imported from the feed "remoteok"
    And a search profile named "Backend" with:
      | titles     | Backend Engineer |
      | location   | Spain            |
      | work_modes | remote           |

  # --- Reading ---

  Scenario: Read the offers that fit a profile
    Given the job board "Remote OK" was imported with:
      | title            | company | description                         | url                    |
      | Backend Engineer | Acme    | Fully remote. Hiring across Europe. | https://remoteok.com/1 |
      | Data Engineer    | Globex  | Fully remote. Hiring across Europe. | https://remoteok.com/2 |
    And the offer reader answers for "Backend Engineer":
      | work_mode | work_mode_evidence | admits_location | admits_location_evidence |
      | remote    | Fully remote       | yes             | Hiring across Europe     |
    When I read the offers
    Then the reading read 1 offers, failed on 0 and left 0 to read
    And the reading of "Backend Engineer" for "Spain" says:
      | work_mode | work_mode_evidence | admits_location | admits_location_evidence |
      | remote    | Fully remote       | yes             | Hiring across Europe     |
    And the offer "Data Engineer" has no readings

  Scenario: An offer is read once
    Given the job board "Remote OK" was imported with:
      | title            | company | description                         | url                    |
      | Backend Engineer | Acme    | Fully remote. Hiring across Europe. | https://remoteok.com/1 |
    And I read the offers
    When I read the offers
    Then the reading read 0 offers, failed on 0 and left 0 to read

  Scenario: An answer whose evidence is not in the description is not kept
    Given the job board "Remote OK" was imported with:
      | title            | company | description                         | url                    |
      | Backend Engineer | Acme    | Fully remote. Hiring across Europe. | https://remoteok.com/1 |
    And the offer reader answers for "Backend Engineer":
      | work_mode | work_mode_evidence | admits_location | admits_location_evidence |
      | remote    | Fully remote       | no              | United States only       |
    When I read the offers
    Then the reading of "Backend Engineer" for "Spain" says:
      | work_mode | work_mode_evidence | admits_location | admits_location_evidence |
      | remote    | Fully remote       |                 |                          |

  Scenario Outline: The title and the location are evidence too
    Given the job board "Remote OK" was imported with:
      | title   | company | location   | description   | url                    |
      | <title> | Acme    | <location> | Fully remote. | https://remoteok.com/1 |
    And the offer reader answers for "<title>":
      | admits_location | admits_location_evidence |
      | no              | <evidence>               |
    When I read the offers
    Then the reading of "<title>" for "Spain" says:
      | admits_location | admits_location_evidence |
      | no              | <evidence>               |

    Examples:
      | title                       | location | evidence              |
      | Backend Engineer - UK       |          | Backend Engineer - UK |
      | US Remote: Backend Engineer | Remote   | US Remote             |
      | Backend Engineer            | USA only | USA only              |

  Scenario Outline: Each offer reader reads its own number of offers at a time
    Given the offer reader is <reader>
    And the job board "Remote OK" was imported with 22 offers as "Backend Engineer"
    When I read the offers
    Then the reading read <read> offers, failed on 0 and left <left> to read

    Examples:
      | reader      | read | left |
      | Groq        | 5    | 17   |
      | Claude Code | 20   | 2    |

  Scenario: Offers without a description are not read
    Given an offer for "Acme" as "Backend Engineer"
    When I read the offers
    Then the reading read 0 offers, failed on 0 and left 0 to read

  Scenario Outline: Only pending offers are read
    Given the job board "Remote OK" was imported with:
      | title            | company | description                         | url                    |
      | Backend Engineer | Acme    | Fully remote. Hiring across Europe. | https://remoteok.com/1 |
    And I <action> the offer "Backend Engineer"
    When I read the offers
    Then the reading read 0 offers, failed on 0 and left 0 to read

    Examples:
      | action    |
      | discarded |
      | promoted  |

  Scenario: A profile without a location is read without the location question
    Given I edit the profile "Backend" to have no location
    And the job board "Remote OK" was imported with:
      | title            | company | description                         | url                    |
      | Backend Engineer | Acme    | Fully remote. Hiring across Europe. | https://remoteok.com/1 |
    And the offer reader answers for "Backend Engineer":
      | work_mode | work_mode_evidence |
      | remote    | Fully remote       |
    When I read the offers
    Then the reading of "Backend Engineer" says:
      | work_mode | work_mode_evidence |
      | remote    | Fully remote       |

  # --- Fitting a profile ---

  Scenario Outline: A read offer is filtered by what its description says
    Given the job board "Remote OK" was imported with:
      | title            | company | description   | url                    |
      | Backend Engineer | Acme    | <description> | https://remoteok.com/1 |
    And the offer reader answers for "Backend Engineer":
      | work_mode   | work_mode_evidence   | admits_location | admits_location_evidence |
      | <work_mode> | <work_mode_evidence> | <admits>        | <admits_evidence>        |
    And I read the offers
    When I view the offer "Backend Engineer"
    Then the offer is <filtered>

    Examples:
      | description                                  | work_mode | work_mode_evidence                   | admits | admits_evidence               | filtered     |
      | Fully remote. Hiring across Europe.          | remote    | Fully remote                         | yes    | Hiring across Europe          | not filtered |
      | Fully remote, anywhere in the United States. | remote    | Fully remote                         | no     | anywhere in the United States | filtered     |
      | Two days a week in our Madrid office.        | hybrid    | Two days a week in our Madrid office | yes    | our Madrid office             | filtered     |
      | Based in our London office.                  | onsite    | Based in our London office           | no     | Based in our London office    | filtered     |
      | Fully remote.                                | remote    | Fully remote                         |        |                               | not filtered |
      | Hiring across Europe.                        |           |                                      | yes    | Hiring across Europe          | not filtered |
      | Python services.                             |           |                                      |        |                               | not filtered |

  Scenario Outline: A read offer that is not a stable job is filtered
    Given the job board "Remote OK" was imported with:
      | title            | company | description   | url                    |
      | Backend Engineer | Acme    | <description> | https://remoteok.com/1 |
    And the offer reader answers for "Backend Engineer":
      | stable   | stable_evidence   |
      | <stable> | <stable_evidence> |
    And I read the offers
    When I view the offer "Backend Engineer"
    Then the offer is <filtered>
    And the reading of "Backend Engineer" for "Spain" says:
      | stable   | stable_evidence   |
      | <stable> | <stable_evidence> |

    Examples:
      | description                         | stable | stable_evidence      | filtered     |
      | Full-time, permanent position.      | yes    | Full-time, permanent | not filtered |
      | Full-time contractor, paid monthly. | yes    | Full-time contractor | not filtered |
      | Task based, up to $500 per task.    | no     | Task based           | filtered     |
      | Up to $85 per hour, flexible hours. | no     | $85 per hour         | filtered     |
      | Six-month contract.                 | no     | Six-month contract   | filtered     |
      | Part-time, 20 hours a week.         | no     | Part-time            | filtered     |
      | Python services.                    |        |                      | not filtered |

  Scenario: An offer that is not a stable job is filtered for a profile that asks for nothing else
    Given I edit the profile "Backend" to have no location and no work modes
    And the job board "Remote OK" was imported with:
      | title            | company | description                      | url                    |
      | Backend Engineer | Acme    | Task based, up to $500 per task. | https://remoteok.com/1 |
    And the offer reader answers for "Backend Engineer":
      | stable | stable_evidence |
      | no     | Task based      |
    And I read the offers
    When I view the offer "Backend Engineer"
    Then the offer is filtered

  Scenario: An offer that has not been read is not filtered by its description
    Given the job board "Remote OK" was imported with:
      | title            | company | description                 | url                    |
      | Backend Engineer | Acme    | Based in our London office. | https://remoteok.com/1 |
    When I view the offer "Backend Engineer"
    Then the offer is not filtered

  Scenario Outline: A profile only filters by what it asks for
    Given I edit the profile "Backend" to have <change>
    And the job board "Remote OK" was imported with:
      | title            | company | description                                    | url                    |
      | Backend Engineer | Acme    | Two days a week in our Austin office, US only. | https://remoteok.com/1 |
    And the offer reader answers for "Backend Engineer":
      | work_mode | work_mode_evidence                   | admits_location | admits_location_evidence |
      | hybrid    | Two days a week in our Austin office | no              | US only                  |
    And I read the offers
    When I view the offer "Backend Engineer"
    Then the offer is <filtered>

    Examples:
      | change                          | filtered     |
      | no work modes                   | filtered     |
      | no location                     | filtered     |
      | no location and no work modes   | not filtered |
      | the work modes "remote, hybrid" | filtered     |

  Scenario: An offer that fits any profile is not filtered
    Given a search profile named "Hybrid in Madrid" with:
      | titles     | Backend Engineer |
      | location   | Spain            |
      | work_modes | hybrid           |
    And the job board "Remote OK" was imported with:
      | title            | company | description                           | url                    |
      | Backend Engineer | Acme    | Two days a week in our Madrid office. | https://remoteok.com/1 |
    And the offer reader answers for "Backend Engineer":
      | work_mode | work_mode_evidence                   | admits_location | admits_location_evidence |
      | hybrid    | Two days a week in our Madrid office | yes             | our Madrid office        |
    And I read the offers
    When I view the offer "Backend Engineer"
    Then the offer is not filtered

  # --- Following the profiles ---

  Scenario: Editing the work modes of a profile changes what is filtered without reading again
    Given the job board "Remote OK" was imported with:
      | title            | company | description                           | url                    |
      | Backend Engineer | Acme    | Two days a week in our Madrid office. | https://remoteok.com/1 |
    And the offer reader answers for "Backend Engineer":
      | work_mode | work_mode_evidence                   | admits_location | admits_location_evidence |
      | hybrid    | Two days a week in our Madrid office | yes             | our Madrid office        |
    And I read the offers
    And I edit the profile "Backend" to have the work modes "remote, hybrid"
    When I view the offer "Backend Engineer"
    Then the offer is not filtered

  Scenario: Changing the location of a profile leaves its offers to be read for the new one
    Given the job board "Remote OK" was imported with:
      | title            | company | description                                  | url                    |
      | Backend Engineer | Acme    | Fully remote, anywhere in the United States. | https://remoteok.com/1 |
    And the offer reader answers for "Backend Engineer":
      | work_mode | work_mode_evidence | admits_location | admits_location_evidence      |
      | remote    | Fully remote       | no              | anywhere in the United States |
    And I read the offers
    And I edit the profile "Backend" to have the location "United States"
    When I view the offer "Backend Engineer"
    Then the offer is not filtered
    And the offer "Backend Engineer" has no reading for "United States"

  Scenario: A pending offer that gets its location is read again with it
    Given the job board "Remote OK" was imported with:
      | title            | company | description   | url                    |
      | Backend Engineer | Acme    | Fully remote. | https://remoteok.com/1 |
    And I read the offers
    And the time is 2026-03-10 15:00
    And the feed "remoteok" publishes an offer for "Acme" as "Backend Engineer" located in "Europe"
    And I import the job board "Remote OK"
    And the offer reader answers for "Backend Engineer":
      | admits_location | admits_location_evidence |
      | yes             | Europe                   |
    When I read the offers
    Then the reading read 1 offers, failed on 0 and left 0 to read
    And the reading of "Backend Engineer" for "Spain" says:
      | admits_location | admits_location_evidence |
      | yes             | Europe                   |

  Scenario Outline: An offer that is no longer pending keeps its readings when it gets its location
    Given the job board "Remote OK" was imported with:
      | title            | company | description   | url                    |
      | Backend Engineer | Acme    | Fully remote. | https://remoteok.com/1 |
    And the offer reader answers for "Backend Engineer":
      | work_mode | work_mode_evidence |
      | remote    | Fully remote       |
    And I read the offers
    And I <action> the offer "Backend Engineer"
    And the time is 2026-03-10 15:00
    And the feed "remoteok" publishes an offer for "Acme" as "Backend Engineer" located in "United Kingdom"
    When I import the job board "Remote OK"
    Then the reading of "Backend Engineer" for "Spain" says:
      | work_mode | work_mode_evidence |
      | remote    | Fully remote       |

    Examples:
      | action    |
      | discarded |
      | promoted  |

  # --- The published location ---

  Scenario Outline: The published location rules out an offer it limits to other countries
    Given the job board "Remote OK" was imported with:
      | title            | company | description   | url                    | location   |
      | Backend Engineer | Acme    | Fully remote. | https://remoteok.com/1 | <location> |
    When I view the offer "Backend Engineer"
    Then the offer is <filtered>

    Examples:
      | location                           | filtered     |
      | USA                                | filtered     |
      | Canada,  USA                       | filtered     |
      | United States or Canada            | filtered     |
      | Germany / Netherlands              | filtered     |
      | Germany,  Ireland,  Spain,  UK     | not filtered |
      | spain                              | not filtered |
      | Worldwide                          | not filtered |
      | Anywhere                           | not filtered |
      | Europe                             | not filtered |
      | EMEA,  UK                          | not filtered |
      | Remote - UK                        | not filtered |
      | San Francisco, CA                  | not filtered |

  Scenario: The published location is the evidence of the location rule
    Given the job board "Remote OK" was imported with:
      | title            | company | description   | url                    | location     |
      | Backend Engineer | Acme    | Fully remote. | https://remoteok.com/1 | Canada,  USA |
    When I view the offer "Backend Engineer"
    Then the filter reason is against the profile "Backend" with:
      | rule      | result  | value | evidence     |
      | title     | passed  |       |              |
      | work_mode | unknown |       |              |
      | location  | failed  | no    | Canada,  USA |
      | stable    | unknown |       |              |

  Scenario: An offer the published location rules out is not read for that location
    Given the job board "Remote OK" was imported with:
      | title            | company | description   | url                    | location |
      | Backend Engineer | Acme    | Fully remote. | https://remoteok.com/1 | USA      |
    When I read the offers
    Then the reading read 0 offers, failed on 0 and left 0 to read

  Scenario: The published location rules out only for a profile whose location it leaves out
    Given I edit the profile "Backend" to have the location "United States"
    And the job board "Remote OK" was imported with:
      | title            | company | description   | url                    | location |
      | Backend Engineer | Acme    | Fully remote. | https://remoteok.com/1 | USA      |
    When I view the offer "Backend Engineer"
    Then the offer is not filtered

  Scenario: A profile without a location is not ruled out by the published location
    Given I delete the profile "Backend"
    And a search profile named "Anywhere" with:
      | titles | Backend Engineer |
    And the job board "Remote OK" was imported with:
      | title            | company | description   | url                    | location |
      | Backend Engineer | Acme    | Fully remote. | https://remoteok.com/1 | USA      |
    When I view the offer "Backend Engineer"
    Then the offer is not filtered

  # --- Errors ---

  Scenario Outline: Without an offer reader nothing is read
    Given the job board "Remote OK" was imported with:
      | title            | company | description                 | url                    |
      | Backend Engineer | Acme    | Based in our London office. | https://remoteok.com/1 |
    And the offer reader is <reader>
    When I read the offers
    Then it is rejected because the offer reader is not available
    And the offer "Backend Engineer" has no readings

    Examples:
      | reader                     |
      | missing                    |
      | Claude Code, not installed |

  Scenario: An offer the reader fails on is left to be read again
    Given the job board "Remote OK" was imported with:
      | title            | company | description                         | url                    |
      | Backend Engineer | Acme    | Fully remote. Hiring across Europe. | https://remoteok.com/1 |
      | Backend Engineer | Globex  | Based in our London office.         | https://remoteok.com/2 |
    And the offer reader fails on the offer of "Globex"
    When I read the offers
    Then the reading read 1 offers, failed on 1 and left 1 to read

  Scenario: A request the reader fails leaves every offer of it to be read again
    Given the offer reader is Claude Code
    And the job board "Remote OK" was imported with:
      | title            | company | description                         | url                    |
      | Backend Engineer | Acme    | Fully remote. Hiring across Europe. | https://remoteok.com/1 |
      | Backend Engineer | Globex  | Based in our London office.         | https://remoteok.com/2 |
    And the offer reader fails
    When I read the offers
    Then the reading read 0 offers, failed on 2 and left 2 to read
