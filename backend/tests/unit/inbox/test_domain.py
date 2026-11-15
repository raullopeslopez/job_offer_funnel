from itertools import product

import pytest

from funnel.modules.inbox.domain import (
    ACTIONS,
    InvalidOfferStatusError,
    OfferAction,
    OfferStatus,
    base_title,
    countries,
    duplicate_key,
    is_title_word,
    next_status,
    url_key,
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


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        pytest.param("https://jobs.example/1", "https://jobs.example/1", id="as-is"),
        pytest.param("https://jobs.example/1/", "https://jobs.example/1", id="trailing-slash"),
        pytest.param(
            "https://jobs.example/1?utm_source=api&utm_medium=feed",
            "https://jobs.example/1",
            id="utm-parameters",
        ),
        pytest.param(
            "https://jobs.example/apply/?job=1&utm_source=api",
            "https://jobs.example/apply?job=1",
            id="keeps-other-parameters",
        ),
    ],
)
def test_url_key_ignores_a_trailing_slash_and_utm_parameters(url: str, expected: str) -> None:
    # Act / Assert
    assert url_key(url) == expected


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        pytest.param("Madrid, Spain", ["Spain"], id="name"),
        pytest.param("spain", ["Spain"], id="ignores-case"),
        pytest.param("USA only", ["United States"], id="short-form"),
        pytest.param("Spain, Portugal", ["Spain", "Portugal"], id="in-order"),
        pytest.param("Germany, Spain, Germany", ["Germany", "Spain"], id="each-once"),
        pytest.param("United States, US", ["United States"], id="name-and-short-form-once"),
        pytest.param("Juba, South Sudan", ["South Sudan"], id="longest-name"),
        pytest.param("Lagos, Nigeria", ["Nigeria"], id="whole-words"),
        pytest.param("Guinea-Bissau", ["Guinea-Bissau"], id="hyphenated-name"),
        pytest.param("Anywhere in the world", ["Worldwide"], id="any-country"),
        pytest.param("Join us remotely", [], id="short-form-in-lowercase"),
        pytest.param("San Francisco, CA", [], id="no-known-country"),
        pytest.param(None, [], id="no-location"),
    ],
)
def test_countries_are_the_known_countries_a_location_names(
    location: str | None, expected: list[str]
) -> None:
    # Act
    found = countries(location)

    # Assert
    assert found == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("title", "expected"),
    [
        pytest.param("Backend Engineer", "Backend Engineer", id="nothing-to-cut"),
        pytest.param("Backend Engineer - Payments", "Backend Engineer", id="dash"),
        pytest.param("Backend Engineer -Payments", "Backend Engineer", id="dash-space-before"),
        pytest.param("Backend Engineer- Payments", "Backend Engineer", id="dash-space-after"),
        pytest.param("Backend Engineer — Payments", "Backend Engineer", id="em-dash"),
        pytest.param("Backend Engineer, Payments", "Backend Engineer", id="comma"),
        pytest.param("Backend Engineer (Remote)", "Backend Engineer", id="parenthesis"),
        pytest.param("Backend Engineer [Remote]", "Backend Engineer", id="bracket"),
        pytest.param("Backend Engineer | Spain", "Backend Engineer", id="vertical-bar"),
        pytest.param("Full-Stack Engineer - Payments", "Full-Stack Engineer", id="hyphen-in-word"),
        pytest.param("  Backend   Engineer  ", "Backend Engineer", id="extra-spaces"),
        pytest.param("(Senior) Backend Engineer", "(Senior) Backend Engineer", id="nothing-left"),
    ],
)
def test_base_title_stops_where_the_role_ends(title: str, expected: str) -> None:
    # Act / Assert
    assert base_title(title) == expected
