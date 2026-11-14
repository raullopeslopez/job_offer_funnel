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
  hand or from an email alert) are never read. At most 5 offers are read at a time,
  so that the offer reader's limits are respected.
  A reading adds three rules to fitting a profile, and only what is known can filter:
  - the offer's work mode, when known, is one of the profile's work modes, if it has any;
  - the offer, when known, can be done living in the profile's location, if it has one;
  - the offer, when known, is a stable job, whatever the profile.
  So an offer that has not been read, or whose description says nothing, is never
  filtered for it. Whether an offer is filtered still follows the current profiles.

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

  Scenario: At most 5 offers are read at a time
    Given the job board "Remote OK" was imported with 6 offers as "Backend Engineer"
    When I read the offers
    Then the reading read 5 offers, failed on 0 and left 1 to read

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

  # --- Errors ---

  Scenario: Without an offer reader nothing is read
    Given the job board "Remote OK" was imported with:
      | title            | company | description                 | url                    |
      | Backend Engineer | Acme    | Based in our London office. | https://remoteok.com/1 |
    And there is no offer reader
    When I read the offers
    Then it is rejected because the offer reader is not available
    And the offer "Backend Engineer" has no readings

  Scenario: An offer the reader fails on is left to be read again
    Given the job board "Remote OK" was imported with:
      | title            | company | description                         | url                    |
      | Backend Engineer | Acme    | Fully remote. Hiring across Europe. | https://remoteok.com/1 |
      | Backend Engineer | Globex  | Based in our London office.         | https://remoteok.com/2 |
    And the offer reader fails on the offer of "Globex"
    When I read the offers
    Then the reading read 1 offers, failed on 1 and left 1 to read
