Feature: Funnel metrics
  As a job seeker
  I want to see how my applications convert from stage to stage, per channel,
  and what I have in progress
  So that I know where I lose applications and which channels work best

  An application has reached a stage when its stage is that one or a later one;
  a closed application counts up to the stage it reached. Open applications count
  too. The conversion from a stage to the next one is the share of the applications
  that reached it which also reached the next one, as a percentage with one decimal.
  It has no rate when no application reached the first stage.
  The active pipeline holds the applications that are neither closed with an
  outcome nor accepted.

  Background:
    Given a company named "Acme"

  # --- Conversion by stage ---

  Scenario: Conversion from each stage to the next one
    Given these applications:
      | stage        | outcome   | channel  |
      | evaluated    |           | portal   |
      | evaluated    | withdrawn | portal   |
      | applied      |           | portal   |
      | applied      | ghosted   | portal   |
      | screening    | rejected  | referral |
      | interviewing |           | referral |
      | offer        |           | referral |
      | accepted     |           | referral |
    When I view the conversion by stage
    Then the conversion is:
      | from         | to           | reached_from | reached_to | rate |
      | evaluated    | applied      | 8            | 6          | 75.0 |
      | applied      | screening    | 6            | 4          | 66.7 |
      | screening    | interviewing | 4            | 3          | 75.0 |
      | interviewing | offer        | 3            | 2          | 66.7 |
      | offer        | accepted     | 2            | 1          | 50.0 |

  Scenario: With no applications there is no conversion rate
    When I view the conversion by stage
    Then the conversion is:
      | from         | to           | reached_from | reached_to | rate |
      | evaluated    | applied      | 0            | 0          |      |
      | applied      | screening    | 0            | 0          |      |
      | screening    | interviewing | 0            | 0          |      |
      | interviewing | offer        | 0            | 0          |      |
      | offer        | accepted     | 0            | 0          |      |

  # --- Conversion by channel ---

  Scenario: Conversion from each stage to the next one, for each channel with applications
    Given these applications:
      | stage        | outcome   | channel  |
      | evaluated    |           | portal   |
      | evaluated    | withdrawn | portal   |
      | applied      |           | portal   |
      | applied      | ghosted   | portal   |
      | screening    | rejected  | referral |
      | interviewing |           | referral |
      | offer        |           | referral |
      | accepted     |           | referral |
    When I view the conversion by channel
    Then the channels are, in order: "portal", "referral"
    And the conversion for channel "portal" is:
      | from         | to           | reached_from | reached_to | rate |
      | evaluated    | applied      | 4            | 2          | 50.0 |
      | applied      | screening    | 2            | 0          | 0.0  |
      | screening    | interviewing | 0            | 0          |      |
      | interviewing | offer        | 0            | 0          |      |
      | offer        | accepted     | 0            | 0          |      |
    And the conversion for channel "referral" is:
      | from         | to           | reached_from | reached_to | rate  |
      | evaluated    | applied      | 4            | 4          | 100.0 |
      | applied      | screening    | 4            | 4          | 100.0 |
      | screening    | interviewing | 4            | 3          | 75.0  |
      | interviewing | offer        | 3            | 2          | 66.7  |
      | offer        | accepted     | 2            | 1          | 50.0  |

  Scenario: With no applications there are no channels
    When I view the conversion by channel
    Then there are no channels

  # --- Active pipeline ---

  Scenario: The active pipeline counts the applications in progress in each stage
    Given these applications:
      | stage        | outcome   | channel  |
      | evaluated    |           | portal   |
      | evaluated    | withdrawn | portal   |
      | applied      |           | portal   |
      | applied      | ghosted   | portal   |
      | screening    | rejected  | referral |
      | interviewing |           | referral |
      | offer        |           | referral |
      | accepted     |           | referral |
    When I view the active pipeline
    Then the active pipeline is:
      | stage        | applications |
      | evaluated    | 1            |
      | applied      | 1            |
      | screening    | 0            |
      | interviewing | 1            |
      | offer        | 1            |
    And there are 4 active applications in total

  Scenario: With no applications the active pipeline is empty
    When I view the active pipeline
    Then the active pipeline is:
      | stage        | applications |
      | evaluated    | 0            |
      | applied      | 0            |
      | screening    | 0            |
      | interviewing | 0            |
      | offer        | 0            |
    And there are 0 active applications in total
