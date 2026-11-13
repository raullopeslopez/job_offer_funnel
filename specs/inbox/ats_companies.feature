Feature: ATS companies
  As a job seeker
  I want to watch the companies I like through the job board of their ATS
  So that their open offers arrive in the inbox without visiting each careers page

  A watched company has a name (required, unique ignoring case and surrounding spaces),
  an ATS (greenhouse, lever or ashby) and the board of the company in that ATS: the
  name that appears in its public careers URL (boards.greenhouse.io/<board>,
  jobs.lever.co/<board>, jobs.ashbyhq.com/<board>).
  Importing a watched company adds to the inbox, as pending, every open offer of its
  board; the ones that fit no search profile are kept as filtered
  (specs/inbox/filtered_offers.feature). Offers already in the inbox are skipped.
  Every imported offer is for the watched company, keeps the link to the original posting
  and the watched company as source. The pending offers of a watched company that are no
  longer on its board are discarded as expired.
  A board that is not available is a normal outcome, not a mistake of ours: the periodic
  import (specs/inbox/job_board_imports.feature) skips it and tries again in the next run.

  Background:
    Given the time is 2026-03-10 09:00
    And a search profile named "Backend" with:
      | titles | Backend Engineer, Python Developer |

  # --- Watching companies ---

  Scenario Outline: Watch a company on its ATS
    When I watch the company "Acme" on "<ats>" with board "acme"
    Then the company "Acme" is watched on "<ats>" with board "acme"

    Examples:
      | ats        |
      | greenhouse |
      | lever      |
      | ashby      |

  Scenario: Surrounding spaces in the name and the board are ignored
    When I watch the company "  Acme  " on "greenhouse" with board "  acme  "
    Then the company "Acme" is watched on "greenhouse" with board "acme"

  Scenario Outline: A watched company needs a name, a known ATS and a board
    When I watch the company "<name>" on "<ats>" with board "<board>"
    Then it is rejected as invalid

    Examples:
      | name | ats        | board |
      |      | greenhouse | acme  |
      | Acme | workday    | acme  |
      | Acme | greenhouse |       |

  Scenario: A name made only of spaces is not valid
    When I watch the company "   " on "greenhouse" with board "acme"
    Then it is rejected as invalid

  Scenario: The same company cannot be watched twice, ignoring case
    Given the company "Acme" is watched on "greenhouse" with board "acme"
    When I watch the company "ACME" on "lever" with board "acme"
    Then it is rejected because the company is already watched

  Scenario: List the watched companies by name
    Given the company "Globex" is watched on "lever" with board "globex"
    And the company "Acme" is watched on "greenhouse" with board "acme"
    When I list the watched companies
    Then the watched companies are:
      | name   | ats        | board  |
      | Acme   | greenhouse | acme   |
      | Globex | lever      | globex |

  Scenario: Stop watching a company keeps its offers in the inbox
    Given the company "Acme" is watched on "greenhouse" with board "acme"
    And the board of "Acme" was imported with:
      | title            | description     | url                                  |
      | Backend Engineer | Python services | https://boards.greenhouse.io/acme/1 |
    When I stop watching the company "Acme"
    Then the company "Acme" is not watched
    And the offer "Backend Engineer" is "pending" and comes from no watched company

  # --- Importing ---

  Scenario: Import every open offer of a watched company
    Given the company "Acme" is watched on "greenhouse" with board "acme"
    And the board of "Acme" publishes:
      | title             | description           | url                                  |
      | Backend Engineer  | Python and PostgreSQL | https://boards.greenhouse.io/acme/1 |
      | Python Developer  | We use Python daily   | https://boards.greenhouse.io/acme/2 |
      | Frontend Engineer | React and Python      | https://boards.greenhouse.io/acme/3 |
    When I import the watched company "Acme"
    Then the import found 3 offers, 3 added, 1 filtered and 0 already in the inbox
    And the pending offers are: "Frontend Engineer", "Python Developer", "Backend Engineer"

  Scenario: Offers already in the inbox are skipped, even if discarded
    Given the company "Acme" is watched on "ashby" with board "acme"
    And an offer for "ACME" as "Backend Engineer" that was discarded
    And the board of "Acme" publishes:
      | title            | description     | url                              |
      | Backend Engineer | Python services | https://jobs.ashbyhq.com/acme/1 |
    When I import the watched company "Acme"
    Then the import found 1 offers, 0 added, 0 filtered and 1 already in the inbox

  Scenario: An imported offer is for the watched company, links to the posting and keeps its source
    Given the company "Acme" is watched on "greenhouse" with board "acme"
    And the board of "Acme" publishes:
      | title            | description     | url                                  |
      | Backend Engineer | Python services | https://boards.greenhouse.io/acme/1 |
    When I import the watched company "Acme"
    Then the offer "Backend Engineer" is for "Acme", links to "https://boards.greenhouse.io/acme/1" and comes from the watched company "Acme"

  Scenario: An offer added by hand has no watched company
    When I add an offer for "Acme" as "Backend Engineer"
    Then the offer "Backend Engineer" comes from no watched company

  Scenario: A watched company can be imported again at once
    Given the company "Acme" is watched on "greenhouse" with board "acme"
    And the board of "Acme" was imported at 2026-03-10 08:59
    And the board of "Acme" publishes no offers
    When I import the watched company "Acme"
    Then the import found 0 offers, 0 added, 0 filtered and 0 already in the inbox

  Scenario: Pending offers that left the board are discarded as expired
    Given the company "Acme" is watched on "greenhouse" with board "acme"
    And the board of "Acme" was imported with:
      | title            | description     | url                                  |
      | Backend Engineer | Python services | https://boards.greenhouse.io/acme/1 |
      | Python Developer | Python services | https://boards.greenhouse.io/acme/2 |
    And I promoted the offer "Python Developer"
    And the board of "Acme" publishes no offers
    When I import the watched company "Acme"
    Then the offer "Backend Engineer" is "discarded" with reason "expired"
    And the offer "Python Developer" is "promoted"

  Scenario: Importing a company does not expire the offers of another
    Given the company "Acme" is watched on "greenhouse" with board "acme"
    And the company "Globex" is watched on "lever" with board "globex"
    And the board of "Globex" was imported with:
      | title            | description     | url                            |
      | Backend Engineer | Python services | https://jobs.lever.co/globex/1 |
    And the board of "Acme" publishes no offers
    When I import the watched company "Acme"
    Then the offer "Backend Engineer" is "pending"

  Scenario: A board that is not available adds nothing
    Given the company "Acme" is watched on "greenhouse" with board "acme"
    And the board of "Acme" is not available
    When I import the watched company "Acme"
    Then it is rejected because the board is not available

  # --- Errors ---

  Scenario: Importing needs an existing watched company
    When I import the watched company "Initech"
    Then it is rejected because the watched company does not exist

  Scenario: Stop watching a company that is not watched
    When I stop watching the company "Initech"
    Then it is rejected because the watched company does not exist
