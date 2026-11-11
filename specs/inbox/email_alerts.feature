Feature: Email alerts
  As a job seeker
  I want the offers of my LinkedIn job alerts in the inbox
  So that the board with the most offers, which has no API for job seekers, fills it too

  A job board with import method "email" (specs/discovery/job_boards.feature) gets its
  offers from its job alert emails. Importing an alert email adds its offers to the inbox
  like a job board import (specs/inbox/job_board_imports.feature): as pending, kept as
  filtered when they fit no search profile (specs/inbox/filtered_offers.feature), and
  skipping the offers already in the inbox. Only LinkedIn's job alerts are read; any
  other email is rejected. Every LinkedIn job alert is read the same way, whatever its
  search: the search profiles, not the alert, decide which offers fit. Each offer links
  to the posting without the email's tracking and comes from the job board that imports
  the alert. An alert only lists new offers, so its offers never expire and there is no
  limit on how often alerts are imported.

  Background:
    Given the time is 2026-03-10 09:00
    And a search profile named "Backend" with:
      | titles | Backend Engineer, Python Developer |
    And a job board named "LinkedIn" imported from the email alert "linkedin"

  # --- Importing ---

  Scenario: Import every offer of a LinkedIn job alert
    Given a LinkedIn job alert with:
      | title             | company | location | job        |
      | Backend Engineer  | Acme    | Spain    | 4480000001 |
      | Python Developer  | Globex  | Remote   | 4480000002 |
      | Frontend Engineer | Initech | Dublin   | 4480000003 |
    When I import the alert
    Then the import found 3 offers, 3 added, 1 filtered and 0 already in the inbox
    And the pending offers are: "Frontend Engineer", "Python Developer", "Backend Engineer"

  Scenario: An offer of an alert links to the posting without tracking
    Given a LinkedIn job alert with:
      | title            | company | location | job        |
      | Backend Engineer | Acme    | Spain    | 4480000001 |
    When I import the alert
    Then the offer "Backend Engineer" links to "https://www.linkedin.com/jobs/view/4480000001/" and comes from the job board "LinkedIn"

  Scenario: An offer that came in an earlier alert is skipped
    Given a LinkedIn job alert with:
      | title            | company | location | job        |
      | Backend Engineer | Acme    | Spain    | 4480000001 |
    And I imported the alert
    When I import the alert
    Then the import found 1 offers, 0 added, 0 filtered and 1 already in the inbox

  Scenario: An alert without offers adds nothing
    Given a LinkedIn job alert with no offers
    When I import the alert
    Then the import found 0 offers, 0 added, 0 filtered and 0 already in the inbox

  # --- Errors ---

  Scenario Outline: An email that is not a LinkedIn job alert is rejected
    Given an email from "<sender>" with a LinkedIn job alert's content
    When I import the alert
    Then it is rejected because the email is not a supported alert

    Examples:
      | sender                           |
      | newsletters-noreply@linkedin.com |
      | donotreply@match.indeed.com      |

  Scenario: An alert that no job board imports is rejected
    Given the job board "LinkedIn" is no longer imported
    And a LinkedIn job alert with:
      | title            | company | location | job        |
      | Backend Engineer | Acme    | Spain    | 4480000001 |
    When I import the alert
    Then it is rejected because no job board imports that email alert
    And there are no offers in the inbox
