Feature: Search profiles
  As a job seeker
  I want to describe once what I am looking for, based on my CV
  So that the app can build the search for every job board I use

  A search profile has a name (required, unique ignoring case and surrounding spaces),
  job titles (at least one; any of them may match), keywords (all of them must appear),
  excluded keywords (none of them may appear), an optional location and the work modes
  it accepts (remote, hybrid, onsite; none means any).
  Every text is trimmed, and repeated words, ignoring case, are kept once.
  In the tables, list values are separated by commas.

  # --- Creating ---

  Scenario: Create a profile with every field
    When I create a search profile with:
      | name              | Backend Python                      |
      | titles            | Backend Engineer, Python Developer  |
      | keywords          | Python, PostgreSQL                  |
      | excluded_keywords | PHP, Manager                        |
      | location          | Madrid                              |
      | work_modes        | remote, hybrid                      |
    Then the search profile has:
      | name              | Backend Python                      |
      | titles            | Backend Engineer, Python Developer  |
      | keywords          | Python, PostgreSQL                  |
      | excluded_keywords | PHP, Manager                        |
      | location          | Madrid                              |
      | work_modes        | remote, hybrid                      |

  Scenario: Create a profile with only a name and a title
    When I create a search profile named "Backend" with titles "Backend Engineer"
    Then the search profile has:
      | name              | Backend          |
      | titles            | Backend Engineer |
      | keywords          |                  |
      | excluded_keywords |                  |
      | work_modes        |                  |
    And the search profile has no location

  Scenario: Repeated words are kept once, ignoring case
    When I create a search profile named "Backend" with titles "Backend Engineer, backend engineer, Python Developer"
    Then the search profile has:
      | titles | Backend Engineer, Python Developer |

  Scenario: Surrounding spaces are ignored
    When I create a search profile named "  Backend  " with titles "  Backend Engineer  "
    Then the search profile has:
      | name   | Backend          |
      | titles | Backend Engineer |

  Scenario Outline: A profile needs valid data
    When I create a search profile named "Backend" with titles "Backend Engineer" and "<field>" set to "<value>"
    Then it is rejected as invalid

    Examples:
      | field      | value          |
      | name       |                |
      | titles     |                |
      | keywords   | Python, ,      |
      | work_modes | remote, office |

  Scenario Outline: Two profiles cannot have the same name, ignoring case
    Given a search profile named "Backend"
    When I create a search profile named "<name>" with titles "Platform Engineer"
    Then it is rejected because the search profile already exists

    Examples:
      | name    |
      | Backend |
      | BACKEND |

  # --- Viewing and listing ---

  Scenario: View a search profile
    Given a search profile named "Backend"
    When I view that search profile
    Then I see the search profile "Backend"

  Scenario: Cannot view a search profile that does not exist
    When I view a nonexistent search profile
    Then it is rejected because the search profile does not exist

  Scenario: Search profiles are listed alphabetically, ignoring case
    Given search profiles named "platform", "Backend" and "Data"
    When I list the search profiles
    Then the search profiles are, in order: "Backend", "Data", "platform"
    And there are 3 search profiles in total

  # --- Editing ---

  Scenario Outline: Edit a field of a search profile
    Given a search profile named "Backend"
    When I change its "<field>" to "<value>"
    Then its "<field>" is "<value>"

    Examples:
      | field             | value             |
      | name              | Backend Python    |
      | titles            | Platform Engineer |
      | keywords          | Go, Kubernetes    |
      | excluded_keywords | Java              |
      | location          | Barcelona         |
      | work_modes        | onsite            |

  Scenario Outline: Clear an optional field
    Given a search profile named "Backend" with keywords "Python", excluded keywords "PHP", location "Madrid" and work modes "remote"
    When I clear its "<field>"
    Then the search profile has no <field>

    Examples:
      | field             |
      | keywords          |
      | excluded_keywords |
      | location          |
      | work_modes        |

  Scenario Outline: The name and the titles cannot be cleared
    Given a search profile named "Backend"
    When I clear its "<field>"
    Then it is rejected as invalid

    Examples:
      | field  |
      | name   |
      | titles |

  Scenario: A profile cannot be renamed to the name of another one, ignoring case
    Given a search profile named "Backend"
    And a search profile named "Platform"
    When I change its "name" to "backend"
    Then it is rejected because the search profile already exists

  Scenario: Cannot edit a search profile that does not exist
    When I change the "name" of a nonexistent search profile to "Backend"
    Then it is rejected because the search profile does not exist

  # --- Deleting ---

  Scenario: Delete a search profile
    Given a search profile named "Backend"
    When I delete that search profile
    Then the search profile no longer exists

  Scenario: Cannot delete a search profile that does not exist
    When I delete a nonexistent search profile
    Then it is rejected because the search profile does not exist
