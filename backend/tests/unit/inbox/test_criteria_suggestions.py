from uuid import uuid7

import pytest

from funnel.modules.discovery.domain import SearchTerms
from funnel.modules.inbox.domain import can_exclude, exclusion_candidates

BACKEND = SearchTerms(["Backend Engineer"], ["Python"], ["Senior"])


@pytest.mark.unit
def test_candidates_are_words_in_3_discarded_titles_and_no_promoted_one() -> None:
    # Arrange
    discarded = [
        (uuid7(), "Lead C++ Engineer"),
        (uuid7(), "lead c++ developer, Lead"),
        (uuid7(), "C++ Lead"),
        (uuid7(), "Staff Engineer"),
    ]

    # Act
    candidates = exclusion_candidates(discarded, promoted_titles=["Staff C++ Developer"])

    # Assert
    assert [(c.word, len(c.offer_ids)) for c in candidates] == [("Lead", 3)]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("word", "expected"),
    [
        pytest.param("Lead", True, id="new-word"),
        pytest.param("senior", False, id="already-excluded"),
        pytest.param("engineer", False, id="part-of-a-title"),
        pytest.param("Python", False, id="a-keyword"),
    ],
)
def test_a_word_can_be_excluded_unless_the_profile_has_it(word: str, expected: bool) -> None:
    # Act
    result = can_exclude(word, BACKEND)

    # Assert
    assert result is expected
