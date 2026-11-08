Feature: Job boards
  As a job seeker
  I want to register the job boards I search in, each with its own search syntax
  So that the app can build a ready-to-open search for each of them

  A job board has a name (required, unique ignoring case and surrounding spaces),
  a search URL template and a syntax: "boolean" (AND, OR, NOT, quotes and parentheses)
  or "keywords" (plain words). The template is an http(s) URL with the placeholder
  {query}, where the search goes, and optionally {location}; no other placeholder
  is allowed.

  # --- Creating ---

  Scenario: Create a job board
    When I create a job board with:
      | name                | LinkedIn                                                                |
      | search_url_template | https://www.linkedin.com/jobs/search/?keywords={query}&location={location} |
      | syntax              | boolean                                                                 |
    Then the job board has:
      | name                | LinkedIn                                                                |
      | search_url_template | https://www.linkedin.com/jobs/search/?keywords={query}&location={location} |
      | syntax              | boolean                                                                 |

  Scenario: The location placeholder is optional
    When I create a job board named "Tecnoempleo" with template "https://www.tecnoempleo.com/ofertas?te={query}" and syntax "keywords"
    Then the job board has:
      | search_url_template | https://www.tecnoempleo.com/ofertas?te={query} |

  Scenario: Surrounding spaces in the name are ignored
    When I create a job board named "  LinkedIn  " with template "https://www.linkedin.com/jobs/search/?keywords={query}" and syntax "boolean"
    Then the job board has:
      | name | LinkedIn |

  Scenario Outline: A job board needs valid data
    When I create a job board named "<name>" with template "<template>" and syntax "<syntax>"
    Then it is rejected as invalid

    Examples:
      | name     | template                                      | syntax   |
      |          | https://jobs.example/search?q={query}         | boolean  |
      | Jobs     | https://jobs.example/search                   | boolean  |
      | Jobs     | https://jobs.example/search?q={query}&r={radius} | boolean |
      | Jobs     | ftp://jobs.example/search?q={query}           | boolean  |
      | Jobs     | not-a-url-{query}                             | boolean  |
      | Jobs     | https://jobs.example/search?q={query}         | regex    |

  Scenario Outline: Two job boards cannot have the same name, ignoring case
    Given a job board named "LinkedIn"
    When I create a job board named "<name>" with template "https://jobs.example/search?q={query}" and syntax "keywords"
    Then it is rejected because the job board already exists

    Examples:
      | name     |
      | LinkedIn |
      | linkedin |

  # --- Viewing and listing ---

  Scenario: View a job board
    Given a job board named "LinkedIn"
    When I view that job board
    Then I see the job board "LinkedIn"

  Scenario: Cannot view a job board that does not exist
    When I view a nonexistent job board
    Then it is rejected because the job board does not exist

  Scenario: Job boards are listed alphabetically, ignoring case
    Given job boards named "tecnoempleo", "LinkedIn" and "Indeed"
    When I list the job boards
    Then the job boards are, in order: "Indeed", "LinkedIn", "tecnoempleo"
    And there are 3 job boards in total

  # --- Editing ---

  Scenario Outline: Edit a field of a job board
    Given a job board named "LinkedIn"
    When I change its "<field>" to "<value>"
    Then its "<field>" is "<value>"

    Examples:
      | field               | value                                         |
      | name                | LinkedIn Jobs                                 |
      | search_url_template | https://www.linkedin.com/jobs/?k={query}      |
      | syntax              | keywords                                      |

  Scenario Outline: An edit needs valid data
    Given a job board named "LinkedIn"
    When I change its "<field>" to "<value>"
    Then it is rejected as invalid
    And its "name" is "LinkedIn"

    Examples:
      | field               | value                       |
      | name                |                             |
      | search_url_template | https://jobs.example/search |
      | syntax              | regex                       |

  Scenario Outline: A required field cannot be cleared
    Given a job board named "LinkedIn"
    When I clear its "<field>"
    Then it is rejected as invalid

    Examples:
      | field               |
      | name                |
      | search_url_template |
      | syntax              |

  Scenario: A job board cannot be renamed to the name of another one, ignoring case
    Given a job board named "LinkedIn"
    And a job board named "Indeed"
    When I change its "name" to "linkedin"
    Then it is rejected because the job board already exists

  Scenario: Cannot edit a job board that does not exist
    When I change the "name" of a nonexistent job board to "LinkedIn"
    Then it is rejected because the job board does not exist

  # --- Deleting ---

  Scenario: Delete a job board
    Given a job board named "LinkedIn"
    When I delete that job board
    Then the job board no longer exists

  Scenario: Cannot delete a job board that does not exist
    When I delete a nonexistent job board
    Then it is rejected because the job board does not exist
