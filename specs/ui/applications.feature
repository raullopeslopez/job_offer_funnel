Feature: Applications screen
  As a job seeker
  I want to see, add and edit my applications from one screen
  So that I follow every job in progress without opening the API docs

  The rules of the applications are those of specs/applications/manage_applications.feature.
  This screen only shows them: every rejection appears as a message, next to its
  field when it belongs to one. The company of an application is chosen among the
  existing companies. Moving an application between stages is not part of this screen.

  Background:
    Given I am signed in with a valid token
    And a company named "Acme"

  # --- Viewing ---

  Scenario: The applications are listed from the most recently created
    Given applications for "Acme" as "A", "B" and "C", created in that order
    When I open the applications
    Then I see the applications, in order: "C", "B", "A"
    And I see 3 applications in total

  Scenario: Each listed application shows its company, stage and channel
    Given an application for "Acme" as "Backend Engineer" via "referral" in stage "applied"
    When I open the applications
    Then the application "Backend Engineer" shows "Acme", "applied" and "referral"

  Scenario: A closed application shows how it ended
    Given an application for "Acme" as "Backend Engineer" closed as "rejected"
    When I open the applications
    Then the application "Backend Engineer" shows "rejected"

  Scenario: Without applications the screen says so
    When I open the applications
    Then I see that there are no applications

  # --- Filtering ---

  Scenario Outline: Filter the applications
    Given these applications for "Acme", created in this order:
      | role | stage        | outcome  | channel  |
      | A    | applied      |          | portal   |
      | B    | screening    | rejected | referral |
      | C    | interviewing |          | referral |
    And I am on the applications
    When I filter the applications by "<filter>" "<value>"
    Then I see the applications, in order: <roles>

    Examples:
      | filter  | value    | roles    |
      | stage   | applied  | "A"      |
      | outcome | rejected | "B"      |
      | channel | referral | "C", "B" |
      | status  | active   | "C", "A" |
      | status  | closed   | "B"      |

  Scenario: Filters combine
    Given these applications for "Acme", created in this order:
      | role | stage   | outcome | channel  |
      | A    | applied |         | portal   |
      | B    | applied |         | referral |
    And I am on the applications
    When I filter the applications by stage "applied" and channel "portal"
    Then I see the applications, in order: "A"

  Scenario: A filter without matches says so
    Given an application for "Acme" as "Backend Engineer"
    And I am on the applications
    When I filter the applications by "outcome" "withdrawn"
    Then I see that there are no applications

  # --- Creating ---

  Scenario: Create an application
    Given I am on the applications
    When I create an application with:
      | company  | Acme                        |
      | role     | Backend Engineer            |
      | channel  | referral                    |
      | priority | high                        |
      | url      | https://acme.example/jobs/1 |
      | notes    | Referred by a former team   |
    Then I see the applications, in order: "Backend Engineer"
    And the application "Backend Engineer" shows "Acme", "evaluated" and "referral"

  Scenario: Create an application that was already applied on a past date
    Given I am on the applications
    When I create an application with:
      | company     | Acme             |
      | role        | Backend Engineer |
      | channel     | portal           |
      | stage       | applied          |
      | occurred_on | 5 days ago       |
    Then the application "Backend Engineer" shows "applied"

  Scenario Outline: An application needs valid data, shown next to its field
    Given I am on the applications
    When I create an application with:
      | company | Acme    |
      | role    | <role>  |
      | channel | portal  |
      | url     | <url>   |
    Then I see an error on the field "<field>"
    And the application is not created

    Examples:
      | role             | url       | field |
      |                  |           | role  |
      | Backend Engineer | not-a-url | url   |

  Scenario: The starting date cannot be in the future
    Given I am on the applications
    When I create an application with:
      | company     | Acme             |
      | role        | Backend Engineer |
      | channel     | portal           |
      | stage       | applied          |
      | occurred_on | tomorrow         |
    Then I see an error on the field "occurred_on"
    And the application is not created

  # --- Detail ---

  Scenario: Open an application to see its data and history
    Given an application for "Acme" as "Backend Engineer" in stage "evaluated" since 2026-03-01
    And it was moved to stage "applied" on 2026-03-04
    And it was closed as "rejected" on 2026-03-09
    And I am on the applications
    When I open the application "Backend Engineer"
    Then I see the application "Backend Engineer" at "Acme", closed as "rejected" in stage "applied"
    And I see its history:
      | stage     | outcome  | occurred_on |
      | evaluated |          | 2026-03-01  |
      | applied   |          | 2026-03-04  |
      | applied   | rejected | 2026-03-09  |

  Scenario: An application that does not exist says so
    When I open an application that does not exist
    Then I see the message "The application does not exist"

  # --- Editing ---

  Scenario: Edit an application
    Given a company named "Globex"
    And an application for "Acme" as "Backend Engineer"
    And I am on the application "Backend Engineer"
    When I edit the application with:
      | company | Globex                       |
      | role    | Platform Engineer            |
      | notes   | Salary range shared by email |
    Then I see the application "Platform Engineer" at "Globex"
    And it shows the notes "Salary range shared by email"

  Scenario: Clear an optional field
    Given an application for "Acme" as "Backend Engineer" with notes "Call back"
    And I am on the application "Backend Engineer"
    When I clear the "notes" of the application
    Then it shows no notes

  Scenario: An edit needs valid data, shown next to its field
    Given an application for "Acme" as "Backend Engineer"
    And I am on the application "Backend Engineer"
    When I edit the application with:
      | role |  |
    Then I see an error on the field "role"

  # --- Deleting ---

  Scenario: Delete an application after confirming
    Given applications for "Acme" as "A" and "B", created in that order
    And I am on the application "A"
    When I delete the application and confirm
    Then I see the applications, in order: "B"

  Scenario: Cancelling the delete keeps the application
    Given an application for "Acme" as "Backend Engineer"
    And I am on the application "Backend Engineer"
    When I delete the application and cancel
    Then I see the application "Backend Engineer" at "Acme"
