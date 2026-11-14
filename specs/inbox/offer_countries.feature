Feature: Offer countries
  As a job seeker
  I want to see the country of the job in every offer of the inbox
  So that I tell at a glance where each offer is from, without opening it

  An imported offer keeps the location its source publishes, as it publishes it: the
  "location" of Remote OK, the "candidate_required_location" of Remotive, the
  "locationRestrictions" of Himalayas, the "jobGeo" of Jobicy, the location of the job
  in Greenhouse, Lever and Ashby, and the location line of each offer of a LinkedIn
  job alert. Offers added by hand, RSS items and offers imported before this feature
  have no location.
  The countries of an offer are the known countries its location names, in the order
  they appear and each once. A country is known by its English name, ignoring case
  (Spain, United Kingdom, Germany...), or by a few common short forms, written in
  capitals: USA and US for United States, UK for United Kingdom, UAE for United Arab
  Emirates. "Worldwide" and "Anywhere" mean the job can be done from any country and
  are shown as "Worldwide". A location that names no known country, such as a city or
  just "Remote", shows as published; an offer without a location shows no country.
  The country is only shown: it changes neither the filter nor the readings.

  Background:
    Given the time is 2026-03-10 09:00
    And a search profile named "Backend" with:
      | titles | Backend Engineer |
    And the job boards imported from a feed:
      | name      | feed      |
      | Remote OK | remoteok  |
      | Remotive  | remotive  |
      | Himalayas | himalayas |
      | Jobicy    | jobicy    |

  # --- Keeping the location ---

  Scenario Outline: An imported offer keeps the location its feed publishes
    Given the feed "<feed>" publishes an offer for "Acme" as "Backend Engineer" located in "Madrid, Spain"
    When I import the job board "<job board>"
    Then the offer "Backend Engineer" is located in "Madrid, Spain"

    Examples:
      | feed      | job board |
      | remoteok  | Remote OK |
      | remotive  | Remotive  |
      | himalayas | Himalayas |
      | jobicy    | Jobicy    |

  Scenario: Several locations of a feed are kept together
    Given the feed "himalayas" publishes an offer for "Acme" as "Backend Engineer" located in "Spain" and "Portugal"
    When I import the job board "Himalayas"
    Then the offer "Backend Engineer" is located in "Spain, Portugal"

  Scenario Outline: An offer of a watched company keeps the location of its board
    Given the company "Acme" is watched on "<ats>" with board "acme"
    And the board of "Acme" publishes "Backend Engineer" located in "Berlin, Germany"
    When I import the watched company "Acme"
    Then the offer "Backend Engineer" is located in "Berlin, Germany"

    Examples:
      | ats        |
      | greenhouse |
      | lever      |
      | ashby      |

  Scenario: An offer of a LinkedIn job alert keeps its location line
    Given a job board named "LinkedIn" imported from the email alert "linkedin"
    And a LinkedIn job alert with:
      | title            | company | location                       | job        |
      | Backend Engineer | Acme    | Dublin, County Dublin, Ireland | 4480000001 |
    When I import the alert
    Then the offer "Backend Engineer" is located in "Dublin, County Dublin, Ireland"

  Scenario: An offer added by hand has no location
    When I add an offer for "Acme" as "Backend Engineer"
    Then the offer "Backend Engineer" has no location

  Scenario: A feed offer without a location has none
    Given the feed "remoteok" publishes an offer for "Acme" as "Backend Engineer" with no location
    When I import the job board "Remote OK"
    Then the offer "Backend Engineer" has no location

  # --- The countries of an offer ---

  Scenario Outline: The countries are the known countries its location names
    Given the feed "remoteok" publishes an offer for "Acme" as "Backend Engineer" located in "<location>"
    When I import the job board "Remote OK"
    Then the offer "Backend Engineer" is from "<countries>"

    Examples:
      | location                     | countries               |
      | Madrid, Spain                | Spain                   |
      | spain                        | Spain                   |
      | Remote - UK                  | United Kingdom          |
      | USA only                     | United States           |
      | San Francisco, US            | United States           |
      | Dubai, UAE                   | United Arab Emirates    |
      | Spain, Portugal              | Spain, Portugal         |
      | Germany, Spain, Germany      | Germany, Spain          |
      | United States or Canada      | United States, Canada   |
      | Worldwide                    | Worldwide               |
      | Anywhere in the world        | Worldwide               |

  Scenario: Short forms count only in capitals
    Given the feed "remoteok" publishes an offer for "Acme" as "Backend Engineer" located in "Join us remotely"
    When I import the job board "Remote OK"
    Then the offer "Backend Engineer" is from no known country

  Scenario Outline: A location that names no known country keeps only its text
    Given the feed "remoteok" publishes an offer for "Acme" as "Backend Engineer" located in "<location>"
    When I import the job board "Remote OK"
    Then the offer "Backend Engineer" is from no known country
    And the offer "Backend Engineer" is located in "<location>"

    Examples:
      | location          |
      | Remote            |
      | San Francisco, CA |
      | Dublin            |
