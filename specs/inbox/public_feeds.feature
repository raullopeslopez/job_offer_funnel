Feature: Public feeds
  As a job seeker
  I want to import into the inbox the offers of remote job boards that publish a feed
  So that new offers arrive without searching by hand

  Feeds: remoteok, remotive, himalayas and jobicy. Importing a feed adds to the inbox,
  as pending, every offer it returns; the ones that fit no search profile are kept as
  filtered (specs/inbox/filtered_offers.feature). Offers already in the inbox are skipped.
  Himalayas' terms rule out reading it whole, so it is searched by the titles of all the
  search profiles; without profiles it returns nothing.
  Every imported offer keeps the link to the original posting and its feed as source.
  To respect each feed's terms, a feed can be imported at most once every 6 hours,
  and the pending offers of a feed that are no longer in it are discarded as expired.

  Background:
    Given the time is 2026-03-10 09:00
    And a search profile named "Backend" with:
      | titles | Backend Engineer, Python Developer |

  # --- Importing ---

  Scenario: Import every offer of a feed
    Given the feed "remoteok" publishes:
      | title              | company | description             | url                     |
      | Backend Engineer   | Acme    | Python and PostgreSQL   | https://remoteok.com/1  |
      | Python Developer   | Globex  | We use Python daily     | https://remoteok.com/2  |
      | Frontend Engineer  | Initech | React and Python        | https://remoteok.com/3  |
    When I import the feed "remoteok"
    Then the import found 3 offers, 3 added, 1 filtered and 0 already in the inbox
    And the pending offers are: "Frontend Engineer", "Python Developer", "Backend Engineer"

  Scenario: Himalayas is searched by the titles of every search profile
    Given a search profile named "Data" with:
      | titles | Data Engineer |
    When I import the feed "himalayas"
    Then the feed "himalayas" was searched for: "Backend Engineer", "Python Developer", "Data Engineer"

  Scenario: Without search profiles Himalayas returns nothing
    Given there are no search profiles
    When I import the feed "himalayas"
    Then the feed "himalayas" was not searched
    And the import found 0 offers, 0 added, 0 filtered and 0 already in the inbox

  Scenario: Offers already in the inbox are skipped, even if discarded
    Given an offer for "Acme" as "Backend Engineer" that was discarded
    And the feed "remoteok" publishes:
      | title            | company | description     | url                    |
      | Backend Engineer | ACME    | Python services | https://remoteok.com/1 |
    When I import the feed "remoteok"
    Then the import found 1 offers, 0 added, 0 filtered and 1 already in the inbox

  Scenario: An imported offer keeps the original link and its feed as source
    Given the feed "himalayas" publishes:
      | title            | company | description     | url                         |
      | Backend Engineer | Acme    | Python services | https://himalayas.app/jobs/1 |
    When I import the feed "himalayas"
    Then the offer "Backend Engineer" links to "https://himalayas.app/jobs/1" and comes from the feed "himalayas"

  Scenario: An offer added by hand has no feed
    When I add an offer for "Acme" as "Backend Engineer"
    Then the offer "Backend Engineer" comes from no feed

  # --- Respecting the feeds' terms ---

  Scenario: A feed cannot be imported again within 6 hours
    Given the feed "remoteok" was imported at 2026-03-10 04:00
    When I import the feed "remoteok"
    Then it is rejected because the feed was imported too recently, until 2026-03-10 10:00

  Scenario: A feed can be imported again after 6 hours
    Given the feed "remoteok" was imported at 2026-03-10 03:00
    And the feed "remoteok" publishes no offers
    When I import the feed "remoteok"
    Then the import found 0 offers, 0 added, 0 filtered and 0 already in the inbox

  Scenario: Each feed has its own limit
    Given the feed "remoteok" was imported at 2026-03-10 08:00
    And the feed "jobicy" publishes no offers
    When I import the feed "jobicy"
    Then the import found 0 offers, 0 added, 0 filtered and 0 already in the inbox

  Scenario: Pending offers that left the feed are discarded as expired
    Given the feed "remoteok" was imported at 2026-03-10 01:00 with:
      | title            | company | description     | url                    |
      | Backend Engineer | Acme    | Python services | https://remoteok.com/1 |
      | Python Developer | Globex  | Python services | https://remoteok.com/2 |
    And I promoted the offer "Python Developer"
    And the feed "remoteok" publishes no offers
    When I import the feed "remoteok"
    Then the offer "Backend Engineer" is "discarded" with reason "expired"
    And the offer "Python Developer" is "promoted"

  Scenario: Offers added by hand never expire
    Given an offer for "Acme" as "Backend Engineer"
    And the feed "remoteok" publishes no offers
    When I import the feed "remoteok"
    Then the offer "Backend Engineer" is "pending"

  Scenario: A feed that is not available adds nothing and can be retried at once
    Given the feed "remotive" is not available
    When I import the feed "remotive"
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

  Scenario: Importing needs an existing feed
    When I import the feed "linkedin"
    Then it is rejected because the feed does not exist
