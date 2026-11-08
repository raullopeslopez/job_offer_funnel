Feature: Metrics screen
  As a job seeker
  I want to see in one screen how my applications convert and what I have in progress
  So that I know where I lose applications and which channels work best without opening the API docs

  The rules of the metrics are those of specs/metrics/funnel_metrics.feature.
  This screen only shows them: each section has a table with the figures and a chart
  of the same figures. A rate is shown as a percentage with one decimal, and as "—"
  when no application reached the first stage of the step.

  Background:
    Given I am signed in with a valid token

  Rule: With applications, the screen shows their conversion and the active pipeline

    Background:
      Given a company named "Acme"
      And these applications for "Acme":
        | stage        | outcome   | channel  |
        | evaluated    |           | portal   |
        | evaluated    | withdrawn | portal   |
        | applied      |           | portal   |
        | applied      | ghosted   | portal   |
        | screening    | rejected  | referral |
        | interviewing |           | referral |
        | offer        |           | referral |
        | accepted     |           | referral |

    Scenario: The conversion from each stage to the next one
      When I open the metrics
      Then I see the conversion by stage:
        | from         | to           | reached_from | reached_to | rate  |
        | evaluated    | applied      | 8            | 6          | 75.0% |
        | applied      | screening    | 6            | 4          | 66.7% |
        | screening    | interviewing | 4            | 3          | 75.0% |
        | interviewing | offer        | 3            | 2          | 66.7% |
        | offer        | accepted     | 2            | 1          | 50.0% |

    Scenario: The conversion for each channel with applications
      When I open the metrics
      Then I see the channels, in order: "portal", "referral"
      And I see the conversion for channel "portal":
        | from         | to           | reached_from | reached_to | rate  |
        | evaluated    | applied      | 4            | 2          | 50.0% |
        | applied      | screening    | 2            | 0          | 0.0%  |
        | screening    | interviewing | 0            | 0          | —     |
        | interviewing | offer        | 0            | 0          | —     |
        | offer        | accepted     | 0            | 0          | —     |

    Scenario: The applications in progress in each stage
      When I open the metrics
      Then I see the active pipeline:
        | stage        | applications |
        | evaluated    | 1            |
        | applied      | 1            |
        | screening    | 0            |
        | interviewing | 1            |
        | offer        | 1            |
      And I see 4 active applications in total

  Rule: Without applications, the screen says so instead of showing empty figures

    Scenario: No applications yet
      When I open the metrics
      Then I see the message "No applications yet: add one to see your metrics"
