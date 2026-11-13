Feature: Sources screen
  As a job seeker
  I want to manage my job boards and the companies I watch on their ATS from one screen
  So that my searches and imports reach every source without Swagger

  The rules of job boards are those of specs/discovery/job_boards.feature; those of the
  watched companies and their imports, of specs/inbox/ats_companies.feature. This screen
  only shows them: every rejection appears as a message, next to its field when it belongs
  to one. The sources are grouped by how their offers reach the inbox, in five blocks, in
  this order: "API import", "Watched companies", "RSS import", "Email alerts" and "Added by
  hand, with a generated search". Each job board is in the block of its import method; the
  job boards are listed alphabetically and the watched companies by name.

  Background:
    Given I am signed in with a valid token

  # --- Blocks ---

  Scenario: The sources are grouped in five blocks by how offers arrive
    When I open the sources
    Then I see the blocks, in order: "API import", "Watched companies", "RSS import", "Email alerts", "Added by hand, with a generated search"

  Scenario: Each job board is in the block of its import method
    Given a job board named "Remote OK" imported from the feed "remoteok"
    And a job board named "Evenbreak" imported from the RSS "https://www.evenbreak.com/jobsrss/?keywords={query}"
    And a job board named "LinkedIn" imported from the email alert "linkedin"
    And a job board named "Indeed"
    When I open the sources
    Then the block "API import" lists the job boards: "Remote OK"
    And the block "RSS import" lists the job boards: "Evenbreak"
    And the block "Email alerts" lists the job boards: "LinkedIn"
    And the block "Added by hand, with a generated search" lists the job boards: "Indeed"

  Scenario: A job board added by hand links to its searches in the profiles
    Given a job board named "Indeed"
    And I am on the sources
    When I open the searches of the job board "Indeed"
    Then I see the profiles

  # --- Job boards ---

  Scenario: The job boards are listed alphabetically
    Given job boards named "tecnoempleo", "LinkedIn" and "Indeed"
    When I open the sources
    Then I see the job boards, in order: "Indeed", "LinkedIn", "tecnoempleo"

  Scenario: Without job boards the blocks say so
    When I open the sources
    Then I see that there are no job boards

  Scenario: Create a job board
    Given I am on the sources
    When I create a job board with:
      | name                | LinkedIn                                                |
      | search_url_template | https://www.linkedin.com/jobs/search/?keywords={query}  |
      | syntax              | boolean                                                 |
    Then I see the job boards, in order: "LinkedIn"
    And the job board "LinkedIn" shows "boolean"

  Scenario Outline: A job board needs valid data, shown next to its field
    Given I am on the sources
    When I create a job board named "<name>" with template "<template>" and syntax "keywords"
    Then I see an error on the field "<field>"
    And the job board is not created

    Examples:
      | name | template                              | field               |
      |      | https://jobs.example/search?q={query} | name                |
      | Jobs | https://jobs.example/search           | search_url_template |

  Scenario: A duplicate job board is rejected with a message
    Given a job board named "LinkedIn"
    And I am on the sources
    When I create a job board named "linkedin" with template "https://jobs.example/search?q={query}" and syntax "keywords"
    Then I see the message "The job board already exists"
    And I see the job boards, in order: "LinkedIn"

  Scenario: Edit a job board
    Given a job board named "LinkedIn" with syntax "boolean"
    And I am on the sources
    When I change the "syntax" of the job board "LinkedIn" to "keywords"
    Then the job board "LinkedIn" shows "keywords"

  Scenario: Start importing a job board from its feed
    Given a job board named "Remote OK"
    And I am on the sources
    When I change the job board "Remote OK" to be imported from the feed "remoteok"
    Then the job board "Remote OK" shows "remoteok"

  Scenario: Start importing a job board from its RSS
    Given a job board named "Evenbreak"
    And I am on the sources
    When I change the job board "Evenbreak" to be imported from the RSS "https://www.evenbreak.com/jobsrss/?keywords={query}"
    Then the job board "Evenbreak" shows "rss"

  Scenario: Start importing a job board from its email alerts
    Given a job board named "LinkedIn"
    And I am on the sources
    When I change the job board "LinkedIn" to be imported from the email alert "linkedin"
    Then the job board "LinkedIn" shows "linkedin alerts"

  Scenario: A feed that another job board imports is rejected with a message
    Given a job board named "Remote OK" imported from the feed "remoteok"
    And a job board named "Remotive"
    And I am on the sources
    When I change the job board "Remotive" to be imported from the feed "remoteok"
    Then I see the message "Another job board already imports that feed"

  Scenario: A job board cannot be renamed to the name of another one
    Given job boards named "Indeed" and "LinkedIn"
    And I am on the sources
    When I change the "name" of the job board "LinkedIn" to "indeed"
    Then I see the message "The job board already exists"
    And I see the job boards, in order: "Indeed", "LinkedIn"

  Scenario: Delete a job board after confirming
    Given job boards named "Indeed" and "LinkedIn"
    And I am on the sources
    When I delete the job board "Indeed" and confirm
    Then I see the job boards, in order: "LinkedIn"

  Scenario: Cancelling the delete keeps the job board
    Given a job board named "LinkedIn"
    And I am on the sources
    When I delete the job board "LinkedIn" and cancel
    Then I see the job boards, in order: "LinkedIn"

  # --- Job boards: importing now ---
  # @component: the E2E tests cannot reach the feeds; component tests cover these.

  @component
  Scenario: Import a job board now
    Given a search profile named "Backend" with the title "Backend Engineer"
    And a job board named "Remote OK" imported from the feed "remoteok"
    And the feed "remoteok" publishes an offer as "Backend Engineer"
    And I am on the sources
    When I import the job board "Remote OK" now
    Then I see the import summary: 1 found, 1 added, 0 filtered, 0 already in the inbox, 0 expired

  @component
  Scenario: A job board imported a moment ago says when it can be imported again
    Given a job board named "Remote OK" imported from the feed "remoteok" 1 minute ago
    And I am on the sources
    When I import the job board "Remote OK" now
    Then I see the message "Remote OK can be imported again in 6 hours"

  # --- Watched companies: viewing ---

  Scenario: The watched companies are listed by name
    Given the company "Globex" is watched on "lever" with board "globex"
    And the company "Acme" is watched on "greenhouse" with board "acme"
    When I open the sources
    Then I see the watched companies, in order: "Acme", "Globex"
    And the watched company "Acme" shows "greenhouse" and "acme"

  Scenario: Without watched companies the section says so
    When I open the sources
    Then I see that there are no watched companies

  # --- Watched companies: watching ---

  Scenario: Watch a company
    Given I am on the sources
    When I watch the company "Acme" on "ashby" with board "acme"
    Then I see the watched companies, in order: "Acme"
    And the watched company "Acme" shows "ashby" and "acme"

  Scenario Outline: A watched company needs a name and a board, shown next to its field
    Given I am on the sources
    When I watch the company "<name>" on "greenhouse" with board "<board>"
    Then I see an error on the field "<field>"
    And the company is not watched

    Examples:
      | name | board | field |
      |      | acme  | name  |
      | Acme |       | board |

  Scenario: The same company cannot be watched twice
    Given the company "Acme" is watched on "greenhouse" with board "acme"
    And I am on the sources
    When I watch the company "acme" on "lever" with board "acme"
    Then I see the message "The company acme is already watched"
    And I see the watched companies, in order: "Acme"

  # --- Watched companies: stopping ---

  Scenario: Stop watching a company after confirming
    Given companies "Acme" and "Globex" are watched
    And I am on the sources
    When I stop watching the company "Acme" and confirm
    Then I see the watched companies, in order: "Globex"

  Scenario: Cancelling keeps the company watched
    Given the company "Acme" is watched on "greenhouse" with board "acme"
    And I am on the sources
    When I stop watching the company "Acme" and cancel
    Then I see the watched companies, in order: "Acme"

  # --- Watched companies: importing ---
  # @component: the E2E tests cannot reach the ATS; component tests cover these.

  @component
  Scenario: Import a watched company
    Given a search profile named "Backend" with the title "Backend Engineer"
    And the company "Acme" is watched on "greenhouse" with board "acme"
    And the board of "Acme" publishes an offer as "Backend Engineer"
    And I am on the sources
    When I import the watched company "Acme"
    Then I see the import summary: 1 found, 1 added, 0 filtered, 0 already in the inbox, 0 expired

  @component
  Scenario: A board that is not available says so
    Given the company "Acme" is watched on "greenhouse" with board "acme"
    And the board of "Acme" is not available
    And I am on the sources
    When I import the watched company "Acme"
    Then I see the message "Board not available"
