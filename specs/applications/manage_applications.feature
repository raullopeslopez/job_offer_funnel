Feature: Manage applications
  As a job seeker
  I want to record every job I consider or apply to
  So that I can see what I have in progress and filter it

  An application belongs to a company and has a role and a channel (required),
  and optionally a priority, the URL of the job posting and notes.
  Channels: portal, referral, recruiter_inbound, direct, networking.
  Priorities: high, medium, low.
  An application starts in stage evaluated (default) or applied; that first
  stage is the first entry of its history. The same company and role may be
  used by more than one application.

  Background:
    Given today is 2026-03-10
    And a company named "Acme"

  # --- Creating ---

  Scenario: Create an application with every field
    When I create an application with:
      | company  | Acme                        |
      | role     | Backend Engineer            |
      | channel  | referral                    |
      | priority | high                        |
      | url      | https://acme.example/jobs/1 |
      | notes    | Referred by a former team   |
    Then the application has:
      | company  | Acme                        |
      | role     | Backend Engineer            |
      | channel  | referral                    |
      | priority | high                        |
      | url      | https://acme.example/jobs/1 |
      | notes    | Referred by a former team   |
    And the application is in stage "evaluated" and still open

  Scenario: Create an application with only the required fields
    When I create an application for "Acme" as "Backend Engineer" via "portal"
    Then the application has no priority, url or notes
    And the application is in stage "evaluated" and still open
    And its history is:
      | stage     | outcome | occurred_on |
      | evaluated |         | 2026-03-10  |

  Scenario: Create an application that was already applied on a past date
    When I create an application for "Acme" as "Backend Engineer" via "portal" in stage "applied" on 2026-03-05
    Then the application is in stage "applied" and still open
    And its history is:
      | stage   | outcome | occurred_on |
      | applied |         | 2026-03-05  |

  Scenario Outline: An application can only start in evaluated or applied
    When I create an application for "Acme" as "Backend Engineer" via "portal" in stage "<stage>"
    Then it is rejected as invalid

    Examples:
      | stage        |
      | screening    |
      | interviewing |
      | offer        |
      | accepted     |

  Scenario: The starting date cannot be in the future
    When I create an application for "Acme" as "Backend Engineer" via "portal" in stage "applied" on 2026-03-11
    Then it is rejected because the date is not valid

  Scenario Outline: An application needs valid data
    When I create an application for "Acme" as "Backend Engineer" via "portal" with "<field>" set to "<value>"
    Then it is rejected as invalid

    Examples:
      | field    | value           |
      | role     |                 |
      | channel  |                 |
      | channel  | carrier_pigeon  |
      | priority | urgent          |
      | url      | not-a-url       |
      | url      | ftp://acme.jobs |

  Scenario: A role made only of spaces is not valid
    When I create an application for "Acme" as "   " via "portal"
    Then it is rejected as invalid

  Scenario: Surrounding spaces in the role are ignored
    When I create an application for "Acme" as "  Backend Engineer  " via "portal"
    Then the application has:
      | role | Backend Engineer |

  Scenario: Cannot create an application for a company that does not exist
    When I create an application for a nonexistent company
    Then it is rejected because the company does not exist

  Scenario: The same company and role can have more than one application
    Given an application for "Acme" as "Backend Engineer"
    When I create an application for "Acme" as "Backend Engineer" via "portal"
    Then there are 2 applications in total

  # --- Editing ---

  Scenario Outline: Edit a field of an application
    Given a company named "Globex"
    And an application for "Acme" as "Backend Engineer"
    When I change its "<field>" to "<value>"
    Then its "<field>" is "<value>"

    Examples:
      | field    | value                         |
      | company  | Globex                        |
      | role     | Platform Engineer             |
      | channel  | networking                    |
      | priority | low                           |
      | url      | https://acme.example/jobs/2   |
      | notes    | Salary range shared by email  |

  Scenario Outline: Clear an optional field
    Given an application for "Acme" as "Backend Engineer" with priority "high", url "https://acme.example/jobs/1" and notes "Call back"
    When I clear its "<field>"
    Then the application has no <field>

    Examples:
      | field    |
      | priority |
      | url      |
      | notes    |

  Scenario: Editing does not change the stage or the history
    Given an application for "Acme" as "Backend Engineer" in stage "applied" since 2026-03-05
    When I change its "role" to "Platform Engineer"
    Then the application is in stage "applied" and still open
    And its history is:
      | stage   | outcome | occurred_on |
      | applied |         | 2026-03-05  |

  Scenario Outline: An edit needs valid data
    Given an application for "Acme" as "Backend Engineer"
    When I change its "<field>" to "<value>"
    Then it is rejected as invalid
    And the application has:
      | role | Backend Engineer |

    Examples:
      | field    | value          |
      | role     |                |
      | channel  | carrier_pigeon |
      | priority | urgent         |
      | url      | not-a-url      |

  Scenario Outline: A required field cannot be cleared
    Given an application for "Acme" as "Backend Engineer"
    When I clear its "<field>"
    Then it is rejected as invalid

    Examples:
      | field   |
      | company |
      | role    |
      | channel |

  Scenario: Cannot move an application to a company that does not exist
    Given an application for "Acme" as "Backend Engineer"
    When I change its company to a nonexistent company
    Then it is rejected because the company does not exist

  Scenario: Cannot edit an application that does not exist
    When I change the "role" of a nonexistent application to "Platform Engineer"
    Then it is rejected because the application does not exist

  # --- Viewing ---

  Scenario: View an application with its history
    Given an application for "Acme" as "Backend Engineer" in stage "evaluated" since 2026-03-01
    And it was moved to stage "applied" on 2026-03-04
    And it was closed as "rejected" on 2026-03-09
    When I view that application
    Then the application has:
      | company | Acme             |
      | role    | Backend Engineer |
    And the application is closed as "rejected" with reached stage "applied"
    And its history is:
      | stage     | outcome  | occurred_on |
      | evaluated |          | 2026-03-01  |
      | applied   |          | 2026-03-04  |
      | applied   | rejected | 2026-03-09  |

  Scenario: Cannot view an application that does not exist
    When I view a nonexistent application
    Then it is rejected because the application does not exist

  # --- Listing ---

  Scenario: Applications are listed from the most recently created
    Given applications for "Acme" as "Backend Engineer", "Data Engineer" and "Platform Engineer", created in that order
    When I list the applications
    Then the applications are, in order: "Platform Engineer", "Data Engineer", "Backend Engineer"
    And there are 3 applications in total

  Scenario Outline: Filter the list by stage, outcome, channel or whether it is still active
    Given these applications for "Acme", created in this order:
      | role | stage        | outcome  | channel  |
      | A    | applied      |          | portal   |
      | B    | screening    | rejected | referral |
      | C    | interviewing |          | referral |
      | D    | applied      | ghosted  | portal   |
    When I list the applications filtered by "<filters>"
    Then the applications are, in order: <roles>

    Examples:
      | filters                       | roles    |
      | stage=applied                 | "D", "A" |
      | outcome=rejected              | "B"      |
      | channel=referral              | "C", "B" |
      | active=true                   | "C", "A" |
      | active=false                  | "D", "B" |
      | stage=applied, channel=portal | "D", "A" |
      | stage=applied, active=true    | "A"      |
      | outcome=withdrawn             |          |

  Scenario Outline: A filter needs a valid value
    When I list the applications filtered by "<filters>"
    Then it is rejected as invalid

    Examples:
      | filters        |
      | stage=lost     |
      | outcome=hired  |
      | channel=fax    |
      | active=maybe   |

  Scenario: The list is paginated
    Given applications for "Acme" as "A", "B", "C", "D" and "E", created in that order
    When I list the applications with limit 2 and offset 2
    Then the applications are, in order: "C", "B"
    And there are 5 applications in total

  Scenario: With no applications the list is empty
    When I list the applications
    Then there are no applications
    And there are 0 applications in total
