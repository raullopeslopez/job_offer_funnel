Feature: Criteria reviews
  As a job seeker
  I want to ask a language model to review my decisions and propose changes to my criteria
  So that it finds what plain counting misses, without ever deciding for me

  A review sends the criteria reviewer the search profiles (name, titles, keywords and
  excluded keywords) and the last 100 imported offers I decided on, from the most recent:
  their title, whether I promoted or discarded them, the discard reason and its word,
  and whether a filtered offer was rescued or rightly filtered. Expired offers are not
  decisions and are not sent. The reviewer answers with proposals, each one changing a
  single rule (titles, keywords or excluded keywords) of one profile, with its reason.
  What the reviewer answers is not trusted. A proposal is kept only if:
  - it names an existing profile, and the new rule is valid and differs from the current one,
  - against the history, it would have filtered no offer I promoted and at least one I
    discarded (what it does is a preview, specs/inbox/criteria_previews.feature).
  Each kept proposal says what it would do and which discarded offers it would have
  filtered. At most 3 proposals are kept, in the reviewer's order. A review saves nothing;
  accepting a proposal is a criteria change (specs/inbox/criteria_changes.feature).
  Without a criteria reviewer the app offers no review and works as always.

  Background:
    Given a job board named "Remote OK" imported from the feed "remoteok"
    And a search profile named "Backend" with:
      | titles            | Backend Engineer |
      | excluded_keywords | Senior           |
    And the job board "Remote OK" was imported with:
      | title                    | company  | description     | url                    |
      | Backend Engineer, Crypto | Acme     | Python services | https://remoteok.com/1 |
      | Backend Engineer Web3    | Globex   | Go services     | https://remoteok.com/2 |
      | Backend Engineer         | Initech  | Python platform | https://remoteok.com/3 |
      | Backend Engineer, Lead   | Hooli    | Rust services   | https://remoteok.com/4 |
    And I discarded the offers of "Acme" and "Globex"
    And I promoted the offer of "Initech"

  # --- Proposals ---

  Scenario: A proposal that passes the history is kept, with what it would do
    Given the criteria reviewer proposes:
      | profile | rule              | value                  | reason                        |
      | Backend | excluded_keywords | Senior, Crypto, Web3   | You discard crypto companies. |
    When I ask for a review
    Then the only proposal is to change the excluded_keywords of "Backend" to "Senior, Crypto, Web3"
    And its reason is "You discard crypto companies."
    And it would have filtered 0 offers I promoted and 2 I discarded
    And it is backed by the offers of "Acme" and "Globex"

  Scenario Outline: A proposal that fails the history or is not valid is dropped
    Given the criteria reviewer proposes:
      | profile   | rule   | value   | reason        |
      | <profile> | <rule> | <value> | A good reason |
    When I ask for a review
    Then there are no proposals

    Examples:
      | profile | rule              | value                       |
      | Backend | keywords          | Rust                        |
      | Backend | excluded_keywords | Senior, Lead                |
      | Backend | excluded_keywords | Senior                      |
      | Backend | titles            |                             |
      | Backend | location          | Spain                       |
      | Data    | excluded_keywords | Crypto                      |

  Scenario: At most 3 proposals are kept, in the reviewer's order
    Given the criteria reviewer proposes:
      | profile | rule              | value                | reason |
      | Backend | excluded_keywords | Senior, Crypto       | First  |
      | Backend | keywords          | Rust                 | Fails  |
      | Backend | excluded_keywords | Senior, Web3         | Second |
      | Backend | excluded_keywords | Senior, Crypto, Web3 | Third  |
      | Backend | excluded_keywords | Senior, Crypto, Lead | Fourth |
    When I ask for a review
    Then the proposals are, in order: "First", "Second", "Third"

  Scenario: A review saves nothing
    Given the criteria reviewer proposes:
      | profile | rule              | value                | reason                        |
      | Backend | excluded_keywords | Senior, Crypto, Web3 | You discard crypto companies. |
    And I asked for a review
    When I view the search profile "Backend"
    Then it has the excluded_keywords "Senior"

  # --- What the reviewer is told ---

  Scenario: The reviewer is told the profiles and my decisions, not the pending or expired offers
    Given the job board "Remote OK" was imported again without the offer of "Globex"
    When I ask for a review
    Then the criteria reviewer was told the profile "Backend" and these decisions:
      | title                    | decision |
      | Backend Engineer         | promoted |
      | Backend Engineer, Crypto | discarded |

  # --- Without a reviewer, and when it fails ---

  Scenario Outline: The review is offered only with a criteria reviewer
    Given the criteria reviewer is <reviewer>
    When I check whether a review is available
    Then it is <availability>

    Examples:
      | reviewer   | availability  |
      | configured | available     |
      | missing    | not available |

  Scenario: Cannot ask for a review without a criteria reviewer
    Given the criteria reviewer is missing
    When I ask for a review
    Then it is rejected because the criteria reviewer is not available

  Scenario: A reviewer that does not answer rejects the review
    Given the criteria reviewer fails
    When I ask for a review
    Then it is rejected because the criteria reviewer did not answer
