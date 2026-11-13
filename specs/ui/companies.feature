Feature: Companies screen
  As a job seeker
  I want to manage my companies from one screen
  So that I keep the data behind my applications up to date without Swagger

  The rules of companies are those of specs/companies/manage_companies.feature.
  This screen only shows them: every rejection appears as a message, next to its
  field when it belongs to one.

  Background:
    Given I am signed in with a valid token

  Scenario: The companies are listed alphabetically
    Given companies named "beta", "Acme" and "Zeta"
    When I open the companies
    Then I see the companies, in order: "Acme", "beta", "Zeta"

  Scenario: Without companies the section says so
    When I open the companies
    Then I see that there are no companies

  Scenario: Create a company
    Given I am on the companies
    When I create a company named "Acme" with website "https://acme.example"
    Then I see the companies, in order: "Acme"
    And the company "Acme" shows "https://acme.example"

  Scenario Outline: A company needs valid data, shown next to its field
    Given I am on the companies
    When I create a company named "<name>" with website "<website>"
    Then I see an error on the field "<field>"
    And the company is not created

    Examples:
      | name | website              | field   |
      |      | https://acme.example | name    |
      | Acme | not-a-url            | website |

  Scenario: A duplicate company is rejected with a message
    Given a company named "Acme"
    And I am on the companies
    When I create a company named "acme" with website "https://acme.example"
    Then I see the message "The company already exists"
    And I see the companies, in order: "Acme"

  Scenario: Edit a company
    Given a company named "Acme" with website "https://acme.example"
    And I am on the companies
    When I change the "website" of the company "Acme" to "https://acme.example/careers"
    Then the company "Acme" shows "https://acme.example/careers"

  Scenario: Clear the website of a company
    Given a company named "Acme" with website "https://acme.example"
    And I am on the companies
    When I clear the "website" of the company "Acme"
    Then the company "Acme" shows no website

  Scenario: A company cannot be renamed to the name of another one
    Given companies named "Acme" and "Globex"
    And I am on the companies
    When I change the "name" of the company "Globex" to "acme"
    Then I see the message "The company already exists"
    And I see the companies, in order: "Acme", "Globex"

  Scenario: Delete a company after confirming
    Given companies named "Acme" and "Globex"
    And I am on the companies
    When I delete the company "Acme" and confirm
    Then I see the companies, in order: "Globex"

  Scenario: Cancelling the delete keeps the company
    Given a company named "Acme"
    And I am on the companies
    When I delete the company "Acme" and cancel
    Then I see the companies, in order: "Acme"

  Scenario: A company with applications cannot be deleted
    Given a company named "Acme"
    And the company "Acme" has an application
    And I am on the companies
    When I delete the company "Acme" and confirm
    Then I see the message "The company has applications and cannot be deleted"
    And I see the companies, in order: "Acme"
