Feature: Settings screen
  As a job seeker
  I want to manage my companies and my job boards from one screen
  So that I keep the data behind my applications and my searches up to date without Swagger

  The rules of companies and job boards are those of specs/companies/manage_companies.feature
  and specs/discovery/job_boards.feature. This screen only shows them: every rejection
  appears as a message, next to its field when it belongs to one. The settings have
  two sections, companies and job boards.

  Background:
    Given I am signed in with a valid token

  # --- Companies ---

  Scenario: The companies are listed alphabetically
    Given companies named "beta", "Acme" and "Zeta"
    When I open the companies in the settings
    Then I see the companies, in order: "Acme", "beta", "Zeta"

  Scenario: Without companies the section says so
    When I open the companies in the settings
    Then I see that there are no companies

  Scenario: Create a company
    Given I am on the companies in the settings
    When I create a company named "Acme" with website "https://acme.example"
    Then I see the companies, in order: "Acme"
    And the company "Acme" shows "https://acme.example"

  Scenario Outline: A company needs valid data, shown next to its field
    Given I am on the companies in the settings
    When I create a company named "<name>" with website "<website>"
    Then I see an error on the field "<field>"
    And the company is not created

    Examples:
      | name | website              | field   |
      |      | https://acme.example | name    |
      | Acme | not-a-url            | website |

  Scenario: A duplicate company is rejected with a message
    Given a company named "Acme"
    And I am on the companies in the settings
    When I create a company named "acme" with website "https://acme.example"
    Then I see the message "The company already exists"
    And I see the companies, in order: "Acme"

  Scenario: Edit a company
    Given a company named "Acme" with website "https://acme.example"
    And I am on the companies in the settings
    When I change the "website" of the company "Acme" to "https://acme.example/careers"
    Then the company "Acme" shows "https://acme.example/careers"

  Scenario: Clear the website of a company
    Given a company named "Acme" with website "https://acme.example"
    And I am on the companies in the settings
    When I clear the "website" of the company "Acme"
    Then the company "Acme" shows no website

  Scenario: A company cannot be renamed to the name of another one
    Given companies named "Acme" and "Globex"
    And I am on the companies in the settings
    When I change the "name" of the company "Globex" to "acme"
    Then I see the message "The company already exists"
    And I see the companies, in order: "Acme", "Globex"

  Scenario: Delete a company after confirming
    Given companies named "Acme" and "Globex"
    And I am on the companies in the settings
    When I delete the company "Acme" and confirm
    Then I see the companies, in order: "Globex"

  Scenario: Cancelling the delete keeps the company
    Given a company named "Acme"
    And I am on the companies in the settings
    When I delete the company "Acme" and cancel
    Then I see the companies, in order: "Acme"

  Scenario: A company with applications cannot be deleted
    Given a company named "Acme"
    And the company "Acme" has an application
    And I am on the companies in the settings
    When I delete the company "Acme" and confirm
    Then I see the message "The company has applications and cannot be deleted"
    And I see the companies, in order: "Acme"

  # --- Job boards ---

  Scenario: The job boards are listed alphabetically
    Given job boards named "tecnoempleo", "LinkedIn" and "Indeed"
    When I open the job boards in the settings
    Then I see the job boards, in order: "Indeed", "LinkedIn", "tecnoempleo"

  Scenario: Without job boards the section says so
    When I open the job boards in the settings
    Then I see that there are no job boards

  Scenario: Create a job board
    Given I am on the job boards in the settings
    When I create a job board with:
      | name                | LinkedIn                                                |
      | search_url_template | https://www.linkedin.com/jobs/search/?keywords={query}  |
      | syntax              | boolean                                                 |
    Then I see the job boards, in order: "LinkedIn"
    And the job board "LinkedIn" shows "boolean"

  Scenario Outline: A job board needs valid data, shown next to its field
    Given I am on the job boards in the settings
    When I create a job board named "<name>" with template "<template>" and syntax "keywords"
    Then I see an error on the field "<field>"
    And the job board is not created

    Examples:
      | name | template                              | field               |
      |      | https://jobs.example/search?q={query} | name                |
      | Jobs | https://jobs.example/search           | search_url_template |

  Scenario: A duplicate job board is rejected with a message
    Given a job board named "LinkedIn"
    And I am on the job boards in the settings
    When I create a job board named "linkedin" with template "https://jobs.example/search?q={query}" and syntax "keywords"
    Then I see the message "The job board already exists"
    And I see the job boards, in order: "LinkedIn"

  Scenario: Edit a job board
    Given a job board named "LinkedIn" with syntax "boolean"
    And I am on the job boards in the settings
    When I change the "syntax" of the job board "LinkedIn" to "keywords"
    Then the job board "LinkedIn" shows "keywords"

  Scenario: Start importing a job board from its feed
    Given a job board named "Remote OK"
    And I am on the job boards in the settings
    When I change the job board "Remote OK" to be imported from the feed "remoteok"
    Then the job board "Remote OK" shows "remoteok"

  Scenario: A feed that another job board imports is rejected with a message
    Given a job board named "Remote OK" imported from the feed "remoteok"
    And a job board named "Remotive"
    And I am on the job boards in the settings
    When I change the job board "Remotive" to be imported from the feed "remoteok"
    Then I see the message "Another job board already imports that feed"

  Scenario: A job board cannot be renamed to the name of another one
    Given job boards named "Indeed" and "LinkedIn"
    And I am on the job boards in the settings
    When I change the "name" of the job board "LinkedIn" to "indeed"
    Then I see the message "The job board already exists"
    And I see the job boards, in order: "Indeed", "LinkedIn"

  Scenario: Delete a job board after confirming
    Given job boards named "Indeed" and "LinkedIn"
    And I am on the job boards in the settings
    When I delete the job board "Indeed" and confirm
    Then I see the job boards, in order: "LinkedIn"

  Scenario: Cancelling the delete keeps the job board
    Given a job board named "LinkedIn"
    And I am on the job boards in the settings
    When I delete the job board "LinkedIn" and cancel
    Then I see the job boards, in order: "LinkedIn"
