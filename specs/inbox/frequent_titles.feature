Feature: Frequent titles among the filtered offers
  As a job seeker
  I want to see which titles keep coming among the offers filtered for having no title of
  a profile
  So that I find the titles my profile does not think of, and add them in one step

  For a search profile, the offers it looks at are the filtered ones
  (specs/inbox/filtered_offers.feature) whose title has none of the profile's titles.
  Their titles are grouped ignoring case and repeated spaces; variants of the same job
  ("Software Engineer, Backend" and "Backend Software Engineer") are not grouped. The
  titles of at least 2 offers are listed, the most frequent first (the first 5), each
  with how many offers have it, how many of them have all the profile's keywords, how
  many pass the profile's work mode, location and contract as far as their reading says
  (specs/inbox/offer_readings.feature), and what adding it to the profile's titles would
  do (specs/inbox/criteria_previews.feature). A title is shown as it is most often
  written; on a tie, as the oldest offer writes it.

  Background:
    Given a job board named "Remote OK" imported from the feed "remoteok"
    And a search profile named "Backend" with:
      | titles   | Backend Engineer |
      | keywords | Python           |
    And the job board "Remote OK" was imported with:
      | title                       | company  | description     | url                    |
      | Software Engineer, Backend  | Acme     | Python services | https://remoteok.com/1 |
      | software engineer,  backend | Globex   | Go services     | https://remoteok.com/2 |
      | Software Engineer, Backend  | Initech  | Python platform | https://remoteok.com/3 |
      | Platform Engineer           | Hooli    | Python tooling  | https://remoteok.com/4 |
      | Platform Engineer           | Umbrella | Rust tooling    | https://remoteok.com/5 |
      | Data Engineer               | Wayne    | Spark pipelines | https://remoteok.com/6 |
      | Backend Engineer            | Stark    | Python services | https://remoteok.com/7 |
      | Backend Engineer            | Lex      | Go services     | https://remoteok.com/8 |

  Scenario: The most frequent titles without a title of the profile
    When I list the frequent titles for the profile "Backend"
    Then 6 offers have no title of the profile
    And the frequent titles are:
      | title                      | offers | with_keywords | reading_passes | entering |
      | Software Engineer, Backend | 3      | 2             | 3              | 2        |
      | Platform Engineer          | 2      | 1             | 2              | 1        |

  Scenario: An offer that is not filtered, or that has a title of the profile, is left out
    Given I discarded the offer of "Acme"
    When I list the frequent titles for the profile "Backend"
    Then 5 offers have no title of the profile
    And the frequent title "Software Engineer, Backend" has 2 offers

  Scenario: Cannot list the frequent titles of a profile that does not exist
    When I list the frequent titles for a nonexistent profile
    Then it is rejected because it does not exist
