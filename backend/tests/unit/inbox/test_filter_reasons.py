from dataclasses import replace

import pytest

from funnel.modules.discovery.domain import SearchTerms, WorkMode
from funnel.modules.inbox.domain import (
    FilterReason,
    ProfileMatch,
    Reading,
    Review,
    ReviewMade,
    Rule,
    RuleCheck,
    RuleResult,
    WordHits,
    check_rules,
    count_filtered,
    filter_reason,
)

PASSED, UNKNOWN, FAILED = RuleResult.PASSED, RuleResult.UNKNOWN, RuleResult.FAILED

REMOTE_IN_SPAIN = SearchTerms(
    titles=["Backend Engineer"],
    keywords=[],
    excluded_keywords=[],
    location="Spain",
    work_modes=[WorkMode.REMOTE],
)


def _profile(name: str, keywords: tuple[str, ...] = ()) -> SearchTerms:
    return SearchTerms(
        titles=["Backend Engineer"], keywords=keywords, excluded_keywords=(), name=name
    )


def _reason(*results: tuple[Rule, RuleResult]) -> FilterReason:
    return FilterReason(None, None, True, [RuleCheck(rule, result) for rule, result in results])


@pytest.mark.unit
def test_lists_only_the_rules_the_profile_asks_for() -> None:
    # Arrange
    match = ProfileMatch(_profile("Backend"), WordHits(titles=["Backend Engineer"]))

    # Act
    checks = check_rules(match)

    # Assert
    assert [(check.rule, check.result) for check in checks] == [
        (Rule.TITLE, PASSED),
        (Rule.STABLE, UNKNOWN),
    ]


@pytest.mark.unit
def test_keywords_say_which_are_found_and_which_are_missing() -> None:
    # Arrange
    terms = _profile("Backend", keywords=("Python", "Django"))
    match = ProfileMatch(terms, WordHits(titles=["Backend Engineer"], keywords=["Python"]))

    # Act
    keywords = check_rules(match)[1]

    # Assert
    assert keywords == RuleCheck(Rule.KEYWORDS, FAILED, found=["Python"], missing=["Django"])


@pytest.mark.unit
@pytest.mark.parametrize(
    ("reading", "expected"),
    [
        pytest.param(None, [UNKNOWN, UNKNOWN, UNKNOWN], id="not-read"),
        pytest.param(Reading(), [UNKNOWN, UNKNOWN, UNKNOWN], id="says-nothing"),
        pytest.param(
            Reading(work_mode=WorkMode.REMOTE, admits_location=True, stable=True),
            [PASSED, PASSED, PASSED],
            id="all-pass",
        ),
        pytest.param(
            Reading(work_mode=WorkMode.HYBRID, admits_location=False, stable=False),
            [FAILED, FAILED, FAILED],
            id="all-fail",
        ),
    ],
)
def test_reading_rules_follow_what_the_reading_says(
    reading: Reading | None, expected: list[RuleResult]
) -> None:
    # Arrange
    match = ProfileMatch(REMOTE_IN_SPAIN, WordHits(titles=["Backend Engineer"]), reading)

    # Act
    checks = check_rules(match)

    # Assert
    assert [check.result for check in checks[1:]] == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("names", "expected"),
    [
        pytest.param(["Zeta", "alpha"], "alpha", id="tie-first-by-name-ignoring-case"),
        pytest.param(["Alpha", "Beta"], "Alpha", id="tie-in-order"),
    ],
)
def test_on_a_tie_the_reference_profile_is_the_first_by_name(
    names: list[str], expected: str
) -> None:
    # Arrange
    matches = [ProfileMatch(_profile(name), WordHits()) for name in names]

    # Act
    reason = filter_reason(matches, has_description=True)

    # Assert
    assert reason.search_profile_name == expected


@pytest.mark.unit
def test_the_reference_profile_is_the_one_failing_the_fewest_rules() -> None:
    # Arrange
    failing_twice = ProfileMatch(_profile("Alpha", keywords=("Go",)), WordHits())
    failing_once = ProfileMatch(_profile("Beta"), WordHits())

    # Act
    reason = filter_reason([failing_twice, failing_once], has_description=True)

    # Assert
    assert reason.search_profile_name == "Beta"


@pytest.mark.unit
def test_without_profiles_the_title_fails() -> None:
    # Act
    reason = filter_reason([], has_description=False)

    # Assert
    assert (reason.search_profile_id, reason.failed, reason.near_miss) == (
        None,
        [Rule.TITLE],
        False,
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("reason", "near_miss"),
    [
        pytest.param(_reason((Rule.TITLE, PASSED), (Rule.KEYWORDS, FAILED)), True, id="one-fails"),
        pytest.param(
            _reason((Rule.TITLE, PASSED), (Rule.KEYWORDS, FAILED), (Rule.STABLE, FAILED)),
            False,
            id="two-fail",
        ),
        pytest.param(_reason((Rule.TITLE, FAILED)), False, id="only-the-title-fails"),
        pytest.param(
            _reason((Rule.TITLE, PASSED), (Rule.KEYWORDS, FAILED), (Rule.STABLE, UNKNOWN)),
            True,
            id="unknown-does-not-count",
        ),
        pytest.param(_reason((Rule.TITLE, PASSED), (Rule.STABLE, PASSED)), False, id="fits"),
    ],
)
def test_a_near_miss_passes_the_title_and_fails_one_rule(
    reason: FilterReason, near_miss: bool
) -> None:
    # Act
    result = reason.near_miss

    # Assert
    assert result is near_miss


@pytest.mark.unit
def test_counts_the_filtered_offers_in_each_rule_they_fail() -> None:
    # Arrange
    reasons = [
        _reason((Rule.TITLE, PASSED), (Rule.STABLE, PASSED)),
        _reason((Rule.TITLE, PASSED), (Rule.KEYWORDS, FAILED)),
        _reason((Rule.TITLE, FAILED), (Rule.KEYWORDS, FAILED)),
    ]

    # Act
    counts = count_filtered(reasons, [])

    # Assert
    assert (counts.filtered, counts.near_misses, counts.failing) == (
        2,
        1,
        {Rule.KEYWORDS: 2, Rule.TITLE: 1},
    )


@pytest.mark.unit
def test_a_near_miss_marked_rightly_filtered_is_no_longer_one() -> None:
    # Arrange
    reason = replace(
        _reason((Rule.TITLE, PASSED), (Rule.KEYWORDS, FAILED)), is_rightly_filtered=True
    )

    # Act
    result = reason.near_miss

    # Assert
    assert result is False


@pytest.mark.unit
def test_counts_the_reviews_made_on_near_misses_and_the_rescues_among_them() -> None:
    # Arrange
    reviews = [
        ReviewMade(Review.RESCUED, [Rule.KEYWORDS]),
        ReviewMade(Review.RIGHTLY_FILTERED, [Rule.LOCATION]),
        ReviewMade(Review.RESCUED, [Rule.TITLE]),
        ReviewMade(Review.RESCUED, [Rule.KEYWORDS, Rule.STABLE]),
    ]

    # Act
    counts = count_filtered([], reviews)

    # Assert
    assert (counts.reviewed_near_misses, counts.rescued_near_misses) == (2, 1)
