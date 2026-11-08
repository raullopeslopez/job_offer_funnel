Feature: Watched companies screen
  As a job seeker
  I want to manage the companies I watch on their ATS and import their offers from one screen
  So that their open offers reach my inbox without Swagger

  The rules of the watched companies and their imports are those of
  specs/inbox/ats_companies.feature. This screen only shows them: every rejection
  appears as a message, next to its field when it belongs to one. The watched
  companies are listed by name.

  Background:
    Given I am signed in with a valid token

  # --- Viewing ---

  Scenario: The watched companies are listed by name
    Given the company "Globex" is watched on "lever" with board "globex"
    And the company "Acme" is watched on "greenhouse" with board "acme"
    When I open the watched companies
    Then I see the watched companies, in order: "Acme", "Globex"
    And the watched company "Acme" shows "greenhouse" and "acme"

  Scenario: Without watched companies the screen says so
    When I open the watched companies
    Then I see that there are no watched companies

  # --- Watching ---

  Scenario: Watch a company
    Given I am on the watched companies
    When I watch the company "Acme" on "ashby" with board "acme"
    Then I see the watched companies, in order: "Acme"
    And the watched company "Acme" shows "ashby" and "acme"

  Scenario Outline: A watched company needs a name and a board, shown next to its field
    Given I am on the watched companies
    When I watch the company "<name>" on "greenhouse" with board "<board>"
    Then I see an error on the field "<field>"
    And the company is not watched

    Examples:
      | name | board | field |
      |      | acme  | name  |
      | Acme |       | board |

  Scenario: The same company cannot be watched twice
    Given the company "Acme" is watched on "greenhouse" with board "acme"
    And I am on the watched companies
    When I watch the company "acme" on "lever" with board "acme"
    Then I see the message "The company acme is already watched"
    And I see the watched companies, in order: "Acme"

  # --- Stopping ---

  Scenario: Stop watching a company after confirming
    Given companies "Acme" and "Globex" are watched
    And I am on the watched companies
    When I stop watching the company "Acme" and confirm
    Then I see the watched companies, in order: "Globex"

  Scenario: Cancelling keeps the company watched
    Given the company "Acme" is watched on "greenhouse" with board "acme"
    And I am on the watched companies
    When I stop watching the company "Acme" and cancel
    Then I see the watched companies, in order: "Acme"

  # --- Importing ---
  # @component: the E2E tests cannot reach the ATS; component tests cover these.

  @component
  Scenario: Import a watched company for a search profile
    Given a search profile named "Backend" with the title "Backend Engineer"
    And the company "Acme" is watched on "greenhouse" with board "acme"
    And the board of "Acme" publishes an offer as "Backend Engineer"
    And I am on the watched companies
    When I import the watched company "Acme" for the profile "Backend"
    Then I see the import summary: 1 found, 1 matching, 1 added, 0 already in the inbox, 0 expired

  @component
  Scenario: A board that is not available says so
    Given a search profile named "Backend" with the title "Backend Engineer"
    And the company "Acme" is watched on "greenhouse" with board "acme"
    And the board of "Acme" is not available
    And I am on the watched companies
    When I import the watched company "Acme" for the profile "Backend"
    Then I see the message "Board not available"

  @component
  Scenario: Importing needs a search profile
    Given the company "Acme" is watched on "greenhouse" with board "acme"
    And I am on the watched companies
    When I import the watched company "Acme" without choosing a profile
    Then I see an error on the field "profile_id"
