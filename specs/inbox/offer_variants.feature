Feature: Offer variants
  As a job seeker
  I want the offers a company publishes for the same role to come together
  So that ten postings of one role read as one role with ten variants, not as repeats

  A company often publishes one posting per team or per country of the same role:
  "Full-Stack Engineer - Payments", "Full-Stack Engineer - Ads Engine". They are
  different jobs, so none is a duplicate (specs/inbox/inbox.feature) and each is still
  promoted or discarded on its own.
  The base title of an offer is its title up to the first of: an opening parenthesis or
  bracket, a comma, or a dash or vertical bar with a space before or after it. A hyphen
  inside a word ("Full-Stack") is part of the word. A title that would be left with no
  base title is its own base title.
  The variants of an offer are the pending offers that are not filtered
  (specs/inbox/filtered_offers.feature), itself included, with its company and its base
  title, both ignoring case and extra spaces. Every offer says its base title and how
  many variants it has; an offer that is not pending, or is filtered, has 1.
  The offers can also be listed with their variants together: the variants go one after
  another, most recent first, where the most recent of them would go. Listed by verdict
  too (specs/inbox/offer_triages.feature), the verdict comes first: only the variants
  within the same group of the verdict go together.

  Background:
    Given today is 2026-03-10

  # --- The base title ---

  Scenario Outline: The base title of an offer
    Given an offer for "Acme" as "<title>"
    When I look at the offer
    Then its base title is "<base title>"

    Examples:
      | title                                             | base title          |
      | Backend Engineer                                  | Backend Engineer    |
      | Backend Engineer - Payments                       | Backend Engineer    |
      | Backend Engineer -Payments                        | Backend Engineer    |
      | Backend Engineer – Payments                       | Backend Engineer    |
      | Backend Engineer, Payments                        | Backend Engineer    |
      | Backend Engineer (Remote)                         | Backend Engineer    |
      | Backend Engineer [Remote]                         | Backend Engineer    |
      | Backend Engineer \| Spain \| Remote               | Backend Engineer    |
      | Backend Engineer (m/f/x) - Payments               | Backend Engineer    |
      | Backend Engineer - Software Engineer - Argentina  | Backend Engineer    |
      | Full-Stack Engineer - Payments                    | Full-Stack Engineer |
      | (Senior) Backend Engineer                         | (Senior) Backend Engineer |

  # --- The variants ---

  Scenario: Offers of a company with the same base title are variants
    Given an offer for "Acme" as "Backend Engineer - Payments"
    And an offer for "Acme" as "Backend Engineer - Platform"
    And an offer for "Acme" as "Backend Engineer"
    When I look at the offer "Backend Engineer - Payments"
    Then it has 3 variants

  Scenario Outline: The company and the base title are compared ignoring case and extra spaces
    Given an offer for "Acme" as "Backend Engineer - Payments"
    And an offer for "<company>" as "<title>"
    When I look at the offer "Backend Engineer - Payments"
    Then it has 2 variants

    Examples:
      | company | title                         |
      | ACME    | Backend Engineer - Platform   |
      | Acme    | backend engineer - Platform   |
      | Acme    | Backend   Engineer - Platform |

  Scenario Outline: Another company or another base title is not a variant
    Given an offer for "Acme" as "Backend Engineer - Payments"
    And an offer for "<company>" as "<title>"
    When I look at the offer "Backend Engineer - Payments"
    Then it has 1 variant

    Examples:
      | company | title                              |
      | Globex  | Backend Engineer - Payments Team   |
      | Acme    | Senior Backend Engineer - Payments |
      | Acme    | Data Engineer - Payments           |

  Scenario Outline: Only pending offers are variants
    Given an offer for "Acme" as "Backend Engineer - Payments"
    And an offer for "Acme" as "Backend Engineer - Platform" that was <decided>
    When I look at the offer "Backend Engineer - <team>"
    Then it has 1 variant

    Examples:
      | decided   | team     |
      | discarded | Payments |
      | discarded | Platform |
      | promoted  | Payments |
      | promoted  | Platform |

  Scenario: A filtered offer is not a variant
    Given a search profile named "Backend" with:
      | titles            | Backend Engineer |
      | excluded_keywords | Junior           |
    And a job board named "Remote OK" imported from the feed "remoteok"
    And the job board "Remote OK" was imported with:
      | title                             | company | description | url                    |
      | Backend Engineer - Payments       | Acme    | Python      | https://remoteok.com/1 |
      | Backend Engineer - Platform       | Acme    | Python      | https://remoteok.com/2 |
      | Backend Engineer - Junior Program | Acme    | Python      | https://remoteok.com/3 |
    When I look at the offer "Backend Engineer - Payments"
    Then it has 2 variants

  # --- Listing with the variants together ---

  Scenario: The variants go together, where the most recent of them would go
    Given these offers, added in this order:
      | company | title                       |
      | Acme    | Backend Engineer - Payments |
      | Globex  | Data Engineer               |
      | Acme    | Backend Engineer - Platform |
      | Initech | Platform Engineer           |
    When I list the pending offers with their variants together
    Then the offers are, in order: "Platform Engineer, Backend Engineer - Platform, Backend Engineer - Payments, Data Engineer"

  Scenario: Without variants, listing them together is the usual order
    Given these offers, added in this order:
      | company | title             |
      | Acme    | Backend Engineer  |
      | Globex  | Data Engineer     |
      | Initech | Platform Engineer |
    When I list the pending offers with their variants together
    Then the offers are, in order: "Platform Engineer, Data Engineer, Backend Engineer"

  Scenario: Listed by verdict too, only the variants with the same verdict go together
    Given these offers, added in this order:
      | company | title                       | verdict |
      | Acme    | Backend Engineer - Payments | OK      |
      | Acme    | Backend Engineer - Platform | KO      |
      | Globex  | Data Engineer               | OK      |
      | Acme    | Backend Engineer - Billing  | OK      |
    When I list the pending offers by verdict with their variants together
    Then the offers are, in order: "Backend Engineer - Billing, Backend Engineer - Payments, Data Engineer, Backend Engineer - Platform"
    And the offer "Backend Engineer - Platform" has 3 variants
