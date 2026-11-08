Feature: Manage companies
  As a job seeker
  I want to keep a list of the companies I apply to
  So that each application belongs to a company and I can see all my applications per company

  A company has a name (required, unique ignoring case and surrounding spaces)
  and an optional website.

  # --- Creating ---

  Scenario: Create a company with a name and a website
    When I create a company named "Acme" with website "https://acme.example"
    Then the company "Acme" exists with website "https://acme.example"

  Scenario: Create a company with only a name
    When I create a company named "Acme"
    Then the company "Acme" exists without a website

  Scenario: Surrounding spaces in the name are ignored
    When I create a company named "  Acme  "
    Then the company "Acme" exists without a website

  Scenario Outline: A company needs a valid name and website
    When I create a company named "<name>" with website "<website>"
    Then it is rejected as invalid

    Examples:
      | name | website              |
      |      | https://acme.example |
      | Acme | not-a-url            |
      | Acme | ftp://acme.example   |

  Scenario: A name made only of spaces is not valid
    When I create a company named "   "
    Then it is rejected as invalid

  Scenario Outline: Two companies cannot have the same name, ignoring case
    Given a company named "Acme"
    When I create a company named "<name>"
    Then it is rejected because the company already exists

    Examples:
      | name |
      | Acme |
      | ACME |
      | acme |

  Scenario: Two companies cannot have the same name, ignoring surrounding spaces
    Given a company named "Acme"
    When I create a company named "  acme  "
    Then it is rejected because the company already exists

  # --- Viewing ---

  Scenario: View a company
    Given a company named "Acme" with website "https://acme.example"
    When I view that company
    Then I see the company "Acme" with website "https://acme.example"

  Scenario: Cannot view a company that does not exist
    When I view a nonexistent company
    Then it is rejected because the company does not exist

  # --- Listing ---

  Scenario: Companies are listed alphabetically, ignoring case
    Given companies named "beta", "Acme" and "Zeta"
    When I list the companies
    Then the companies are, in order: "Acme", "beta", "Zeta"
    And there are 3 companies in total

  Scenario: The list is paginated
    Given companies named "A", "B", "C", "D" and "E"
    When I list the companies with limit 2 and offset 2
    Then the companies are, in order: "C", "D"
    And there are 5 companies in total

  Scenario: With no companies the list is empty
    When I list the companies
    Then there are no companies
    And there are 0 companies in total
