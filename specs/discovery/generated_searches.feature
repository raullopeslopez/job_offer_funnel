Feature: Generated searches
  As a job seeker
  I want the app to build, from one search profile, the search for every job board
  So that I only open the links instead of writing each search by hand

  The query follows the syntax of each job board:
  - boolean (e.g. LinkedIn): titles joined with OR, keywords with AND, exclusions with NOT.
  - minus (e.g. Indeed): titles joined with OR, keywords side by side, exclusions as -word.
  - keywords: no operators, so there is one search per title with the keywords after it;
    exclusions cannot be expressed and are left out.
  Words with spaces go between double quotes in boolean and minus queries.
  The URL is the job board's template with the query and the location URL-encoded;
  without a location, {location} is left empty. Work modes do not change the URL:
  they are shown so the job board's own filter can be set.

  Background:
    Given a search profile named "Backend" with:
      | titles            | Backend Engineer, Python Developer |
      | keywords          | Python, PostgreSQL                 |
      | excluded_keywords | PHP, Project Manager               |
      | location          | Kuala Lumpur                       |
      | work_modes        | remote, hybrid                     |

  # --- Queries per syntax ---

  Scenario Outline: The query follows the syntax of the job board
    Given a job board named "Board" with syntax "<syntax>"
    When I generate the searches of the profile "Backend"
    Then the searches for "Board" have the queries:
      | query   |
      | <query> |

    Examples:
      | syntax  | query                                                                                                     |
      | boolean | ("Backend Engineer" OR "Python Developer") AND Python AND PostgreSQL NOT PHP NOT "Project Manager" |
      | minus   | ("Backend Engineer" OR "Python Developer") Python PostgreSQL -PHP -"Project Manager"                |

  Scenario: A keywords job board gets one search per title, without exclusions
    Given a job board named "Board" with syntax "keywords"
    When I generate the searches of the profile "Backend"
    Then the searches for "Board" have the queries:
      | query                                 |
      | Backend Engineer Python PostgreSQL    |
      | Python Developer Python PostgreSQL    |

  Scenario Outline: A profile with a single title and nothing else
    Given a search profile named "Simple" with:
      | titles | Backend Engineer |
    And a job board named "Board" with syntax "<syntax>"
    When I generate the searches of the profile "Simple"
    Then the searches for "Board" have the queries:
      | query   |
      | <query> |

    Examples:
      | syntax   | query              |
      | boolean  | "Backend Engineer" |
      | minus    | "Backend Engineer" |
      | keywords | Backend Engineer   |

  # --- URLs ---

  Scenario: The URL fills the template with the query and the location, URL-encoded
    Given a search profile named "Simple" with:
      | titles   | Backend Engineer |
      | location | Kuala Lumpur     |
    And a job board named "Board" with syntax "keywords" and template "https://jobs.example/search?q={query}&l={location}"
    When I generate the searches of the profile "Simple"
    Then the searches for "Board" have the URLs:
      | url                                                              |
      | https://jobs.example/search?q=Backend%20Engineer&l=Kuala%20Lumpur |

  Scenario: Without a location, the location placeholder is left empty
    Given a search profile named "Simple" with:
      | titles | Backend Engineer |
    And a job board named "Board" with syntax "keywords" and template "https://jobs.example/search?q={query}&l={location}"
    When I generate the searches of the profile "Simple"
    Then the searches for "Board" have the URLs:
      | url                                                  |
      | https://jobs.example/search?q=Backend%20Engineer&l= |

  # --- Every job board ---

  Scenario: There are searches for every job board, in alphabetical order
    Given a job board named "LinkedIn" with syntax "boolean"
    And a job board named "Indeed" with syntax "minus"
    And a job board named "Glints" with syntax "keywords"
    When I generate the searches of the profile "Backend"
    Then the job boards with searches are, in order: "Glints", "Indeed", "LinkedIn"
    And the work modes to filter by are "remote, hybrid"

  Scenario: Without job boards there are no searches
    When I generate the searches of the profile "Backend"
    Then there are no searches

  Scenario: Cannot generate the searches of a profile that does not exist
    When I generate the searches of a nonexistent profile
    Then it is rejected because the search profile does not exist
