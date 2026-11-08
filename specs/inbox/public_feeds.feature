Feature: Public feeds
  As a job seeker
  I want to import into the inbox the offers of remote job boards that publish a feed
  So that the offers matching my profile arrive without searching by hand

  Feeds: remoteok, remotive, himalayas and jobicy. Importing a feed for a search
  profile adds to the inbox, as pending, each offer of the feed that matches it:
  - one of the profile's titles appears in the offer's title,
  - all of its keywords appear in the title or the description,
  - none of its excluded keywords appears in the title.
  Words are compared ignoring case. Offers already in the inbox are skipped.
  Every imported offer keeps the link to the original posting and its feed as source.
  To respect each feed's terms, a feed can be imported at most once every 6 hours,
  and the pending offers of a feed that are no longer in it are discarded as expired.

  Background:
    Given the time is 2026-03-10 09:00
    And a search profile named "Backend" with:
      | titles            | Backend Engineer, Python Developer |
      | keywords          | Python                             |
      | excluded_keywords | Senior                             |

  # --- Importing ---

  Scenario: Import the offers of a feed that match the profile
    Given the feed "remoteok" publishes:
      | title              | company | description             | url                     |
      | Backend Engineer   | Acme    | Python and PostgreSQL   | https://remoteok.com/1  |
      | Python Developer   | Globex  | We use Python daily     | https://remoteok.com/2  |
      | Frontend Engineer  | Initech | React and Python        | https://remoteok.com/3  |
    When I import the feed "remoteok" for the profile "Backend"
    Then the import found 3 offers, 2 matching, 2 added and 0 already in the inbox
    And the pending offers are: "Python Developer", "Backend Engineer"

  Scenario Outline: An offer matches when a title, every keyword and no exclusion fit
    Given the feed "remoteok" publishes:
      | title   | company | description   | url                    |
      | <title> | Acme    | <description> | https://remoteok.com/1 |
    When I import the feed "remoteok" for the profile "Backend"
    Then the import found 1 offers, <matching> matching, <matching> added and 0 already in the inbox

    Examples:
      | title                    | description         | matching |
      | Backend Engineer         | Python services     | 1        |
      | backend engineer (Remote) | We love python      | 1        |
      | Backend Engineer, Python | Go services         | 1        |
      | Backend Engineer         | Go services         | 0        |
      | Data Engineer            | Python pipelines    | 0        |
      | Senior Backend Engineer  | Python services     | 0        |
      | Backend Engineer         | Mentor senior staff | 1        |

  Scenario: Offers already in the inbox are skipped, even if discarded
    Given an offer for "Acme" as "Backend Engineer" that was discarded
    And the feed "remoteok" publishes:
      | title            | company | description     | url                    |
      | Backend Engineer | ACME    | Python services | https://remoteok.com/1 |
    When I import the feed "remoteok" for the profile "Backend"
    Then the import found 1 offers, 1 matching, 0 added and 1 already in the inbox

  Scenario: An imported offer keeps the original link and its feed as source
    Given the feed "himalayas" publishes:
      | title            | company | description     | url                         |
      | Backend Engineer | Acme    | Python services | https://himalayas.app/jobs/1 |
    When I import the feed "himalayas" for the profile "Backend"
    Then the offer "Backend Engineer" links to "https://himalayas.app/jobs/1" and comes from the feed "himalayas"

  Scenario: An offer added by hand has no feed
    When I add an offer for "Acme" as "Backend Engineer"
    Then the offer "Backend Engineer" comes from no feed

  # --- Respecting the feeds' terms ---

  Scenario: A feed cannot be imported again within 6 hours
    Given the feed "remoteok" was imported at 2026-03-10 04:00
    When I import the feed "remoteok" for the profile "Backend"
    Then it is rejected because the feed was imported too recently, until 2026-03-10 10:00

  Scenario: A feed can be imported again after 6 hours
    Given the feed "remoteok" was imported at 2026-03-10 03:00
    And the feed "remoteok" publishes no offers
    When I import the feed "remoteok" for the profile "Backend"
    Then the import found 0 offers, 0 matching, 0 added and 0 already in the inbox

  Scenario: Each feed has its own limit
    Given the feed "remoteok" was imported at 2026-03-10 08:00
    And the feed "jobicy" publishes no offers
    When I import the feed "jobicy" for the profile "Backend"
    Then the import found 0 offers, 0 matching, 0 added and 0 already in the inbox

  Scenario: Pending offers that left the feed are discarded as expired
    Given the feed "remoteok" was imported at 2026-03-10 01:00 with:
      | title            | company | description     | url                    |
      | Backend Engineer | Acme    | Python services | https://remoteok.com/1 |
      | Python Developer | Globex  | Python services | https://remoteok.com/2 |
    And I promoted the offer "Python Developer"
    And the feed "remoteok" publishes no offers
    When I import the feed "remoteok" for the profile "Backend"
    Then the offer "Backend Engineer" is "discarded" with reason "expired"
    And the offer "Python Developer" is "promoted"

  Scenario: Offers added by hand never expire
    Given an offer for "Acme" as "Backend Engineer"
    And the feed "remoteok" publishes no offers
    When I import the feed "remoteok" for the profile "Backend"
    Then the offer "Backend Engineer" is "pending"

  Scenario: A feed that is not available adds nothing and can be retried at once
    Given the feed "remotive" is not available
    When I import the feed "remotive" for the profile "Backend"
    Then it is rejected because the feed is not available
    And the feed "remotive" has never been imported

  # --- Feeds ---

  Scenario: The feeds show when they were last imported
    Given the feed "remoteok" was imported at 2026-03-10 04:00
    When I list the feeds
    Then the feeds are:
      | feed      | last_imported_at    | next_import_at      |
      | himalayas |                     |                     |
      | jobicy    |                     |                     |
      | remoteok  | 2026-03-10 04:00    | 2026-03-10 10:00    |
      | remotive  |                     |                     |

  # --- Errors ---

  Scenario Outline: Importing needs an existing feed and profile
    When I import the feed "<feed>" for the profile "<profile>"
    Then it is rejected because <reason>

    Examples:
      | feed     | profile  | reason                                  |
      | linkedin | Backend  | the feed does not exist                 |
      | remoteok | Missing  | the search profile does not exist       |
