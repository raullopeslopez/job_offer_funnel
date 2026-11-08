Feature: Stage transitions on the application detail
  As a job seeker
  I want to move an application forward, close it or undo my last change from its detail
  So that the funnel reflects where each application stands without opening the API docs

  The rules of the transitions are those of specs/applications/stage_transitions.feature.
  This screen only shows them: every rejected transition appears as a message and leaves
  the application as it was. Without a date, a transition is recorded with today's date.

  Background:
    Given I am signed in with a valid token
    And a company named "Acme"

  # --- Moving forward ---

  Scenario: Move an application to a later stage
    Given an application for "Acme" as "Backend Engineer" in stage "applied" since 2026-03-01
    And I am on the application "Backend Engineer"
    When I move the application to stage "interviewing"
    Then I see the application in stage "interviewing"
    And its history ends with stage "interviewing" dated today

  Scenario: Move an application with a past date and a note
    Given an application for "Acme" as "Backend Engineer" in stage "applied" since 2026-03-01
    And I am on the application "Backend Engineer"
    When I move the application to stage "screening" on 2026-03-04 with the note "Call with recruiter"
    Then I see the application in stage "screening"
    And I see its history:
      | stage     | outcome | occurred_on | note                |
      | applied   |         | 2026-03-01  |                     |
      | screening |         | 2026-03-04  | Call with recruiter |

  # --- Closing ---

  Scenario: Close an application with an outcome
    Given an application for "Acme" as "Backend Engineer" in stage "applied" since 2026-03-01
    And I am on the application "Backend Engineer"
    When I close the application as "rejected"
    Then I see the application closed as "rejected" in stage "applied"

  # --- Rejected transitions ---

  Scenario Outline: A transition the funnel does not allow is shown as a message
    Given an application for "Acme" as "Backend Engineer" in stage "<stage>" since 2026-03-01
    And I am on the application "Backend Engineer"
    When I <action>
    Then I see the message "<message>"
    And I see the application in stage "<stage>"

    Examples:
      | stage     | action                                     | message                                 |
      | screening | move the application to stage "applied"    | Cannot move from screening to applied   |
      | evaluated | close the application as "rejected"        | Cannot close as rejected from evaluated |

  Scenario: A transition cannot be dated before the previous one
    Given an application for "Acme" as "Backend Engineer" in stage "applied" since 2026-03-05
    And I am on the application "Backend Engineer"
    When I move the application to stage "screening" on 2026-03-04
    Then I see the message "2026-03-04 is before the previous transition (2026-03-05)"
    And I see the application in stage "applied"

  # --- Undoing the last transition ---

  Scenario: Undo the last transition after confirming
    Given an application for "Acme" as "Backend Engineer" in stage "applied" since 2026-03-01
    And it was closed as "rejected" on 2026-03-09
    And I am on the application "Backend Engineer"
    When I undo the last transition and confirm
    Then I see the application in stage "applied"
    And I see its history:
      | stage   | outcome | occurred_on | note |
      | applied |         | 2026-03-01  |      |

  Scenario: Cancelling the undo keeps the last transition
    Given an application for "Acme" as "Backend Engineer" in stage "applied" since 2026-03-01
    And it was closed as "rejected" on 2026-03-09
    And I am on the application "Backend Engineer"
    When I undo the last transition and cancel
    Then I see the application closed as "rejected" in stage "applied"

  Scenario: The first stage cannot be undone
    Given an application for "Acme" as "Backend Engineer" in stage "applied" since 2026-03-01
    And I am on the application "Backend Engineer"
    When I undo the last transition and confirm
    Then I see the message "The first stage cannot be undone; delete the application instead"
    And I see the application in stage "applied"
