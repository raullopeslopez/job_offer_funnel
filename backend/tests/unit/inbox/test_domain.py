from itertools import product

import pytest

from funnel.modules.inbox.domain import (
    ACTIONS,
    InvalidOfferStatusError,
    OfferAction,
    OfferStatus,
    duplicate_key,
    is_title_word,
    next_status,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("word", "title", "expected"),
    [
        pytest.param("Senior", "Senior Backend Engineer", True, id="first-word"),
        pytest.param("senior", "Senior Backend Engineer", True, id="ignores-case"),
        pytest.param("C++", "Senior C++ Developer", True, id="symbols"),
        pytest.param("Django", "Python Developer (Django)", True, id="in-parentheses"),
        pytest.param("Back", "Senior Backend Engineer", False, id="part-of-a-word"),
        pytest.param("Junior", "Senior Backend Engineer", False, id="not-in-title"),
    ],
)
def test_is_title_word_matches_whole_words_ignoring_case(
    word: str, title: str, *, expected: bool
) -> None:
    # Act / Assert
    assert is_title_word(word, title) is expected


# Copied from the spec: the status each action starts from and leads to.
ALLOWED = [
    (OfferStatus.PENDING, OfferAction.DISCARD, OfferStatus.DISCARDED),
    (OfferStatus.DISCARDED, OfferAction.RESTORE, OfferStatus.PENDING),
    (OfferStatus.PENDING, OfferAction.PROMOTE, OfferStatus.PROMOTED),
]
NOT_ALLOWED = [
    (status, action)
    for status, action in product(OfferStatus, OfferAction)
    if ACTIONS[action][0] is not status
]


@pytest.mark.parametrize(("current", "action", "expected"), ALLOWED, ids=str)
def test_allowed_action_leads_to_its_status(
    current: OfferStatus, action: OfferAction, expected: OfferStatus
) -> None:
    # Act
    status = next_status(current, action)

    # Assert
    assert status is expected


@pytest.mark.parametrize(("current", "action"), NOT_ALLOWED, ids=str)
def test_action_from_another_status_is_rejected(current: OfferStatus, action: OfferAction) -> None:
    # Act / Assert
    with pytest.raises(InvalidOfferStatusError):
        next_status(current, action)


@pytest.mark.parametrize(
    ("company", "title"),
    [
        pytest.param("ACME", "backend engineer", id="case"),
        pytest.param("  Acme ", "Backend   Engineer", id="spaces"),
    ],
)
def test_duplicate_key_ignores_case_and_extra_spaces(company: str, title: str) -> None:
    # Act / Assert
    assert duplicate_key(company, title) == duplicate_key("Acme", "Backend Engineer")


def test_duplicate_key_keeps_company_and_title_apart() -> None:
    # Act / Assert
    assert duplicate_key("Acme Backend", "Engineer") != duplicate_key("Acme", "Backend Engineer")
