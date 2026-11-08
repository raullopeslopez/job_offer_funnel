Feature: Searches screen
  As a job seeker
  I want to manage my search profiles and open their searches from one screen
  So that I search every job board without writing each query by hand

  The rules of the profiles and of the generated queries are those of
  specs/discovery/search_profiles.feature and specs/discovery/generated_searches.feature.
  This screen only shows them: every rejection appears as a message, next to its
  field when it belongs to one. In the tables, list values are separated by commas.

  Background:
    Given I am signed in with a valid token

  # --- Viewing ---

  Scenario: The profiles are listed alphabetically
    Given search profiles named "platform", "Backend" and "Data"
    When I open the searches
    Then I see the profiles, in order: "Backend", "Data", "platform"

  Scenario: Without profiles the screen says so
    When I open the searches
    Then I see that there are no profiles

  # --- Creating ---

  Scenario: Create a profile
    Given I am on the searches
    When I create a profile with:
      | name              | Backend Python                     |
      | titles            | Backend Engineer, Python Developer |
      | keywords          | Python, PostgreSQL                 |
      | excluded_keywords | PHP                                |
      | location          | Madrid                             |
      | work_modes        | remote, hybrid                     |
    Then I see the profiles, in order: "Backend Python"
    And the profile "Backend Python" shows "Backend Engineer, Python Developer"

  Scenario Outline: A profile needs valid data, shown next to its field
    Given I am on the searches
    When I create a profile named "<name>" with titles "<titles>"
    Then I see an error on the field "<field>"
    And the profile is not created

    Examples:
      | name    | titles           | field  |
      |         | Backend Engineer | name   |
      | Backend |                  | titles |

  Scenario: A duplicate profile is rejected with a message
    Given a search profile named "Backend"
    And I am on the searches
    When I create a profile named "backend" with titles "Platform Engineer"
    Then I see the message "The search profile already exists"
    And I see the profiles, in order: "Backend"

  # --- Editing ---

  Scenario: Edit a profile
    Given a search profile named "Backend"
    And I am on the searches
    When I change the "titles" of the profile "Backend" to "Platform Engineer, Go Developer"
    Then the profile "Backend" shows "Platform Engineer, Go Developer"

  Scenario: Clear an optional field
    Given a search profile named "Backend" with location "Madrid"
    And I am on the searches
    When I clear the "location" of the profile "Backend"
    Then the profile "Backend" shows no location

  Scenario: A profile cannot be renamed to the name of another one
    Given search profiles named "Backend" and "Platform"
    And I am on the searches
    When I change the "name" of the profile "Platform" to "backend"
    Then I see the message "The search profile already exists"
    And I see the profiles, in order: "Backend", "Platform"

  # --- Deleting ---

  Scenario: Delete a profile after confirming
    Given search profiles named "Backend" and "Platform"
    And I am on the searches
    When I delete the profile "Backend" and confirm
    Then I see the profiles, in order: "Platform"

  Scenario: Cancelling the delete keeps the profile
    Given a search profile named "Backend"
    And I am on the searches
    When I delete the profile "Backend" and cancel
    Then I see the profiles, in order: "Backend"

  # --- Generated searches ---

  Scenario: A profile shows its searches for every job board, in alphabetical order
    Given a search profile named "Backend" with titles "Backend Engineer, Python Developer" and work modes "remote, hybrid"
    And a job board named "LinkedIn" with syntax "boolean"
    And a job board named "Glints" with syntax "keywords"
    And I am on the searches
    When I open the searches of the profile "Backend"
    Then the job boards with searches are, in order: "Glints", "LinkedIn"
    And "Glints" has 2 searches and "LinkedIn" has 1
    And I see that the work modes to filter by are "remote, hybrid"

  Scenario: Each search opens the job board with its query
    Given a search profile named "Simple" with titles "Backend Engineer"
    And a job board named "Board" with syntax "keywords" and template "https://jobs.example/search?q={query}"
    And I am on the searches
    When I open the searches of the profile "Simple"
    Then the search "Backend Engineer" of "Board" links to "https://jobs.example/search?q=Backend%20Engineer"

  Scenario: Without job boards the profile says there are no searches
    Given a search profile named "Backend"
    And I am on the searches
    When I open the searches of the profile "Backend"
    Then I see that there are no searches
