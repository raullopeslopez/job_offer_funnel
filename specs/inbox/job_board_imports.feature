Feature: Job board imports
  As a job seeker
  I want to import into the inbox the offers of the job boards that publish a feed or an RSS
  So that new offers arrive without searching by hand

  A job board with import method "api" (specs/discovery/job_boards.feature) is imported
  from its feed: remoteok, remotive, himalayas or jobicy. Importing it adds to the inbox,
  as pending, every offer the feed returns; the ones that fit no search profile are kept
  as filtered (specs/inbox/filtered_offers.feature). Offers already in the inbox are skipped.
  Himalayas' terms rule out reading it whole, so it is searched by the titles of all the
  search profiles; without profiles it returns nothing.
  Jobicy publishes only its latest offers, newest first and in pages of 100: an offer
  leaves its feed within hours, long before it closes. So its first 3 pages are read, and
  an offer that is no longer in its feed is not taken as closed.
  A job board with import method "rss" is read once for each title of all the search
  profiles, with the title in the {query} of its RSS URL template; without profiles it is
  not read. Each RSS item is an offer whose title reads "Company: Title" (Evenbreak's
  convention): the company is what comes before the first colon and the title what comes
  after it. Items without a company, a title or a link are not offers, and an item found
  by several titles is one offer.
  Every imported offer keeps the link to the original posting and its job board as source.
  Some feeds publish the title and the company with HTML character references ("&#038;"
  or "&amp;" for "&"): an offer keeps the characters they stand for, never the reference.
  To respect each source's terms, a job board can be imported at most once every 6 hours,
  and its pending imported offers that are no longer in its feed or RSS are discarded as
  expired, except Jobicy's.
  A feed, RSS or ATS board that is not available is a normal outcome, not a mistake of ours:
  the sources are outside services we do not control. The periodic import (every 6 hours)
  reports it as skipped, adds nothing and tries again in the next run, so the run does
  not fail. Any other error, such as our own API failing, does make the run fail.

  Background:
    Given the time is 2026-03-10 09:00
    And a search profile named "Backend" with:
      | titles | Backend Engineer, Python Developer |
    And the job boards imported from a feed:
      | name      | feed      |
      | Remote OK | remoteok  |
      | Remotive  | remotive  |
      | Himalayas | himalayas |
      | Jobicy    | jobicy    |

  # --- Importing ---

  Scenario: Import every offer of a job board
    Given the feed "remoteok" publishes:
      | title              | company | description             | url                     |
      | Backend Engineer   | Acme    | Python and PostgreSQL   | https://remoteok.com/1  |
      | Python Developer   | Globex  | We use Python daily     | https://remoteok.com/2  |
      | Frontend Engineer  | Initech | React and Python        | https://remoteok.com/3  |
    When I import the job board "Remote OK"
    Then the import found 3 offers, 3 added, 1 filtered and 0 already in the inbox
    And the pending offers are: "Frontend Engineer", "Python Developer", "Backend Engineer"

  Scenario: Himalayas is searched by the titles of every search profile
    Given a search profile named "Data" with:
      | titles | Data Engineer |
    When I import the job board "Himalayas"
    Then the feed "himalayas" was searched for: "Backend Engineer", "Python Developer", "Data Engineer"

  Scenario: Without search profiles Himalayas returns nothing
    Given there are no search profiles
    When I import the job board "Himalayas"
    Then the feed "himalayas" was not searched
    And the import found 0 offers, 0 added, 0 filtered and 0 already in the inbox

  Scenario: Offers already in the inbox are skipped, even if discarded
    Given an offer for "Acme" as "Backend Engineer" that was discarded
    And the feed "remoteok" publishes:
      | title            | company | description     | url                    |
      | Backend Engineer | ACME    | Python services | https://remoteok.com/1 |
    When I import the job board "Remote OK"
    Then the import found 1 offers, 0 added, 0 filtered and 1 already in the inbox

  Scenario: An imported offer keeps the original link and its job board as source
    Given the feed "himalayas" publishes:
      | title            | company | description     | url                         |
      | Backend Engineer | Acme    | Python services | https://himalayas.app/jobs/1 |
    When I import the job board "Himalayas"
    Then the offer "Backend Engineer" links to "https://himalayas.app/jobs/1" and comes from the job board "Himalayas"

  Scenario: HTML character references in the title and the company are read as their characters
    Given the feed "jobicy" publishes:
      | title                     | company                                      | description     | url                  |
      | R&#038;D Backend Engineer | Quest Defense Systems &amp; Solutions, Inc.  | Python services | https://jobicy.com/1 |
    When I import the job board "Jobicy"
    Then the pending offers are: "R&D Backend Engineer"
    And the offer "R&D Backend Engineer" is for the company "Quest Defense Systems & Solutions, Inc."

  Scenario Outline: Jobicy is read page by page, up to 3 pages
    Given the feed "jobicy" publishes <pages> pages of 2 offers
    When I import the job board "Jobicy"
    Then the import found <found> offers, <found> added, <found> filtered and 0 already in the inbox

    Examples:
      | pages | found |
      | 1     | 2     |
      | 3     | 6     |
      | 4     | 6     |

  # --- Importing from an RSS ---

  Scenario: Import a job board from its RSS, searching by every title
    Given a job board named "Evenbreak" imported from the RSS "https://www.evenbreak.com/jobsrss/?keywords={query}"
    And the RSS of "Evenbreak" publishes for "Backend Engineer":
      | title                    | description           | link                              |
      | Acme: Backend Engineer   | Python and PostgreSQL | https://www.evenbreak.com/job/1/  |
      | Initech: Data Analyst    | Excel and SQL         | https://www.evenbreak.com/job/2/  |
    And the RSS of "Evenbreak" publishes for "Python Developer":
      | title                    | description           | link                              |
      | Globex: Python Developer | We use Python daily   | https://www.evenbreak.com/job/3/  |
    When I import the job board "Evenbreak"
    Then the RSS of "Evenbreak" was read at:
      | https://www.evenbreak.com/jobsrss/?keywords=Backend%20Engineer |
      | https://www.evenbreak.com/jobsrss/?keywords=Python%20Developer |
    And the import found 3 offers, 3 added, 1 filtered and 0 already in the inbox
    And the offer "Python Developer" links to "https://www.evenbreak.com/job/3/" and comes from the job board "Evenbreak"

  Scenario Outline: The company of an RSS item is what comes before the first colon
    Given a job board named "Evenbreak" imported from the RSS "https://www.evenbreak.com/jobsrss/?keywords={query}"
    And the RSS of "Evenbreak" publishes for "Backend Engineer":
      | title       | description     | link                             |
      | <rss_title> | Python services | https://www.evenbreak.com/job/1/ |
    When I import the job board "Evenbreak"
    Then the pending offers are, with their company:
      | company   | title   |
      | <company> | <title> |

    Examples:
      | rss_title                        | company  | title                      |
      | CGI: Python Developers           | CGI      | Python Developers          |
      | Acme Ltd : Backend Engineer      | Acme Ltd | Backend Engineer           |
      | Acme: Backend Engineer: Payments | Acme     | Backend Engineer: Payments |

  Scenario Outline: An RSS item without a company, a title or a link is not an offer
    Given a job board named "Evenbreak" imported from the RSS "https://www.evenbreak.com/jobsrss/?keywords={query}"
    And the RSS of "Evenbreak" publishes for "Backend Engineer":
      | title       | description     | link   |
      | <rss_title> | Python services | <link> |
    When I import the job board "Evenbreak"
    Then the import found 0 offers, 0 added, 0 filtered and 0 already in the inbox

    Examples:
      | rss_title              | link                             |
      | Backend Engineer       | https://www.evenbreak.com/job/1/ |
      | : Backend Engineer     | https://www.evenbreak.com/job/1/ |
      | Acme:                  | https://www.evenbreak.com/job/1/ |
      | Acme: Backend Engineer |                                  |

  Scenario: An RSS item found by several titles is one offer
    Given a job board named "Evenbreak" imported from the RSS "https://www.evenbreak.com/jobsrss/?keywords={query}"
    And the RSS of "Evenbreak" publishes for "Backend Engineer":
      | title                  | description     | link                             |
      | Acme: Backend Engineer | Python services | https://www.evenbreak.com/job/1/ |
    And the RSS of "Evenbreak" publishes for "Python Developer":
      | title                  | description     | link                             |
      | Acme: Backend Engineer | Python services | https://www.evenbreak.com/job/1/ |
    When I import the job board "Evenbreak"
    Then the import found 1 offers, 1 added, 0 filtered and 0 already in the inbox

  Scenario: The title goes into the RSS URL encoded
    Given there are no search profiles
    And a search profile named "C#" with:
      | titles | C# Developer |
    And a job board named "Evenbreak" imported from the RSS "https://www.evenbreak.com/jobsrss/?keywords={query}"
    When I import the job board "Evenbreak"
    Then the RSS of "Evenbreak" was read at:
      | https://www.evenbreak.com/jobsrss/?keywords=C%23%20Developer |

  Scenario: Without search profiles an RSS is not read
    Given there are no search profiles
    And a job board named "Evenbreak" imported from the RSS "https://www.evenbreak.com/jobsrss/?keywords={query}"
    When I import the job board "Evenbreak"
    Then the RSS of "Evenbreak" was not read
    And the import found 0 offers, 0 added, 0 filtered and 0 already in the inbox

  Scenario: Pending offers that left the RSS are discarded as expired
    Given a job board named "Evenbreak" imported from the RSS "https://www.evenbreak.com/jobsrss/?keywords={query}"
    And the job board "Evenbreak" was imported at 2026-03-10 01:00 with:
      | title            | company | description     | url                              |
      | Backend Engineer | Acme    | Python services | https://www.evenbreak.com/job/1/ |
    And the RSS of "Evenbreak" publishes nothing
    When I import the job board "Evenbreak"
    Then the offer "Backend Engineer" is "discarded" with reason "expired"

  Scenario Outline: An RSS that cannot be read adds nothing and can be retried at once
    Given a job board named "Evenbreak" imported from the RSS "https://www.evenbreak.com/jobsrss/?keywords={query}"
    And the RSS of "Evenbreak" <problem>
    When I import the job board "Evenbreak"
    Then it is rejected because the feed is not available
    And the job board "Evenbreak" has never been imported

    Examples:
      | problem            |
      | is not available   |
      | is not a valid RSS |

  # --- Respecting the terms of each source ---

  Scenario: A job board cannot be imported again within 6 hours
    Given the job board "Remote OK" was imported at 2026-03-10 04:00
    When I import the job board "Remote OK"
    Then it is rejected because the job board was imported too recently, until 2026-03-10 10:00

  Scenario: A job board can be imported again after 6 hours
    Given the job board "Remote OK" was imported at 2026-03-10 03:00
    And the feed "remoteok" publishes no offers
    When I import the job board "Remote OK"
    Then the import found 0 offers, 0 added, 0 filtered and 0 already in the inbox

  Scenario: Each job board has its own limit
    Given the job board "Remote OK" was imported at 2026-03-10 08:00
    And the feed "jobicy" publishes no offers
    When I import the job board "Jobicy"
    Then the import found 0 offers, 0 added, 0 filtered and 0 already in the inbox

  Scenario: Pending offers that left the feed are discarded as expired
    Given the job board "Remote OK" was imported at 2026-03-10 01:00 with:
      | title            | company | description     | url                    |
      | Backend Engineer | Acme    | Python services | https://remoteok.com/1 |
      | Python Developer | Globex  | Python services | https://remoteok.com/2 |
    And I promoted the offer "Python Developer"
    And the feed "remoteok" publishes no offers
    When I import the job board "Remote OK"
    Then the offer "Backend Engineer" is "discarded" with reason "expired"
    And the offer "Python Developer" is "promoted"

  Scenario: Pending offers that left Jobicy's feed are not expired
    Given the job board "Jobicy" was imported at 2026-03-10 01:00 with:
      | title            | company | description     | url                  |
      | Backend Engineer | Acme    | Python services | https://jobicy.com/1 |
    And the feed "jobicy" publishes no offers
    When I import the job board "Jobicy"
    Then the offer "Backend Engineer" is "pending"

  Scenario: Offers added by hand never expire, even in an imported job board
    Given an offer for "Acme" as "Backend Engineer" from "Remote OK"
    And the feed "remoteok" publishes no offers
    When I import the job board "Remote OK"
    Then the offer "Backend Engineer" is "pending"

  Scenario: A feed that is not available adds nothing and can be retried at once
    Given the feed "remotive" is not available
    When I import the job board "Remotive"
    Then it is rejected because the feed is not available
    And the job board "Remotive" has never been imported

  # --- Last import ---

  Scenario: The job boards show when they were last imported
    Given a job board named "LinkedIn"
    And a job board named "Evenbreak" imported from the RSS "https://www.evenbreak.com/jobsrss/?keywords={query}"
    And the job board "Remote OK" was imported at 2026-03-10 04:00
    When I list the job boards
    Then the job boards are:
      | name      | import_method | last_imported_at | next_import_at   |
      | Evenbreak | rss           |                  |                  |
      | Himalayas | api           |                  |                  |
      | Jobicy    | api           |                  |                  |
      | LinkedIn  | none          |                  |                  |
      | Remote OK | api           | 2026-03-10 04:00 | 2026-03-10 10:00 |
      | Remotive  | api           |                  |                  |

  # --- Errors ---

  Scenario: Only a job board with an import method can be imported
    Given a job board named "LinkedIn"
    When I import the job board "LinkedIn"
    Then it is rejected because the job board is not imported

  Scenario: A job board imported from its email alerts is not imported on demand
    Given a job board named "LinkedIn" imported from the email alert "linkedin"
    When I import the job board "LinkedIn"
    Then it is rejected because the job board is imported from its email alerts

  Scenario: Importing needs an existing job board
    When I import a nonexistent job board
    Then it is rejected because the job board does not exist
