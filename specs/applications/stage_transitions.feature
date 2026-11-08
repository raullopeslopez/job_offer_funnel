Feature: Application stage transitions
  As a job seeker
  I want to record how each application moves forward or closes
  So that I know where it stands in the funnel and where I lose applications

  Stages, in order: evaluated, applied, screening, interviewing, offer, accepted.
  Outcomes: rejected, ghosted, withdrawn, offer_declined.
  A closed application keeps the stage it reached.

  Background:
    Given today is 2026-03-10

  # --- Moving forward ---

  Scenario Outline: Move to any later stage, skipping stages if needed
    Given an application in stage "<from>"
    When I move it to stage "<to>"
    Then the application is in stage "<to>" and still open

    Examples:
      | from         | to           |
      | evaluated    | applied      |
      | evaluated    | screening    |
      | applied      | screening    |
      | applied      | interviewing |
      | screening    | interviewing |
      | interviewing | offer        |
      | offer        | accepted     |

  Scenario Outline: Cannot move back or repeat the current stage
    Given an application in stage "<from>"
    When I move it to stage "<to>"
    Then it is rejected as an invalid transition
    And the application is still in stage "<from>"

    Examples:
      | from      | to           |
      | screening | applied      |
      | offer     | interviewing |
      | applied   | evaluated    |
      | applied   | applied      |

  # --- Closing with an outcome ---

  Scenario Outline: Close an application with an outcome allowed in its stage
    Given an application in stage "<stage>"
    When I close it as "<outcome>"
    Then the application is closed as "<outcome>" with reached stage "<stage>"

    Examples:
      | stage        | outcome        |
      | evaluated    | withdrawn      |
      | interviewing | withdrawn      |
      | applied      | rejected       |
      | offer        | rejected       |
      | applied      | ghosted        |
      | interviewing | ghosted        |
      | offer        | offer_declined |

  Scenario Outline: Cannot close with an outcome that makes no sense in the stage
    Given an application in stage "<stage>"
    When I close it as "<outcome>"
    Then it is rejected as an invalid transition
    And the application is still in stage "<stage>" and open

    Examples:
      | stage        | outcome        |
      | evaluated    | rejected       |
      | evaluated    | ghosted        |
      | applied      | offer_declined |
      | interviewing | offer_declined |

  # --- Finished applications ---

  Scenario Outline: An accepted or closed application (except ghosted) allows no more changes
    Given an application closed as "<outcome>" with reached stage "<stage>"
    When I move it to stage "<to>"
    Then it is rejected as an invalid transition

    Examples:
      | outcome        | stage     | to           |
      | rejected       | screening | interviewing |
      | withdrawn      | applied   | screening    |
      | offer_declined | offer     | accepted     |

  Scenario: An accepted application cannot be closed with an outcome
    Given an application in stage "accepted"
    When I close it as "withdrawn"
    Then it is rejected as an invalid transition

  # --- Reactivating a ghosted application ---

  Scenario Outline: A ghosted application is reactivated by moving it to its reached stage or later
    Given an application closed as "ghosted" with reached stage "screening"
    When I move it to stage "<to>"
    Then the application is in stage "<to>" and still open

    Examples:
      | to           |
      | screening    |
      | interviewing |

  Scenario: A ghosted application cannot be reactivated in a stage before the one it reached
    Given an application closed as "ghosted" with reached stage "interviewing"
    When I move it to stage "screening"
    Then it is rejected as an invalid transition

  # --- Transition date ---

  Scenario: Without a date, the transition is recorded with today's date
    Given an application in stage "applied"
    When I move it to stage "screening"
    Then the latest transition is dated 2026-03-10

  Scenario: A transition can be recorded with a past date
    Given an application that moved to stage "applied" on 2026-03-01
    When I move it to stage "screening" on 2026-03-04
    Then the latest transition is dated 2026-03-04

  Scenario Outline: The date cannot be in the future or before the previous transition
    Given an application that moved to stage "applied" on 2026-03-05
    When I move it to stage "screening" on <date>
    Then it is rejected as an invalid date
    And the application is still in stage "applied"

    Examples:
      | date       |
      | 2026-03-11 |
      | 2026-03-04 |

  # --- History ---

  Scenario: Every transition is kept in the history, in order
    Given an application that moved to stage "applied" on 2026-03-01
    And I moved it to stage "screening" on 2026-03-03 with the note "Call with recruiter"
    And I closed it as "ghosted" on 2026-03-09
    When I view its transition history
    Then the history is:
      | from      | to        | outcome | date       | note                |
      |           | applied   |         | 2026-03-01 |                     |
      | applied   | screening |         | 2026-03-03 | Call with recruiter |
      | screening | screening | ghosted | 2026-03-09 |                     |

  # --- Undoing the last transition ---

  Scenario: Undoing a move brings the application back to the previous stage
    Given an application that moved to stage "applied" on 2026-03-01
    And I moved it to stage "screening" on 2026-03-03 with the note "Call with recruiter"
    When I undo its last transition
    Then the application is still in stage "applied" and open
    And the latest transition is dated 2026-03-01

  Scenario: Undoing a closure reopens the application in its reached stage
    Given an application that moved to stage "interviewing" on 2026-03-01
    And I closed it as "rejected" on 2026-03-09
    When I undo its last transition
    Then the application is still in stage "interviewing" and open

  Scenario: Undoing a reactivation leaves the application ghosted again
    Given an application that moved to stage "screening" on 2026-03-01
    And I closed it as "ghosted" on 2026-03-05
    And I moved it to stage "interviewing" on 2026-03-08 with the note "They wrote back"
    When I undo its last transition
    Then the application is closed as "ghosted" with reached stage "screening"

  Scenario: The first stage of an application cannot be undone
    Given an application that moved to stage "applied" on 2026-03-01
    When I undo its last transition
    Then it is rejected as an invalid transition
    And the application is still in stage "applied" and open

  # --- Errors ---

  Scenario: Cannot move an application that does not exist
    When I move a nonexistent application to stage "screening"
    Then it is rejected because the application does not exist

  Scenario: Cannot undo a transition of an application that does not exist
    When I undo the last transition of a nonexistent application
    Then it is rejected because the application does not exist
