import pytest

from funnel.modules.inbox.domain import FrequentTitle, UntitledOffer, frequent_titles


def _offer(title: str, *, has_keywords: bool = True) -> UntitledOffer:
    return UntitledOffer(title, has_keywords=has_keywords, reading_passes=True)


@pytest.mark.unit
def test_groups_titles_ignoring_case_and_spaces_and_keeps_the_most_written_form() -> None:
    # Arrange
    offers = [
        _offer("platform  engineer"),
        _offer("Platform Engineer", has_keywords=False),
        _offer("Platform Engineer"),
        _offer("Data Engineer"),
    ]

    # Act
    titles = frequent_titles(offers)

    # Assert
    assert titles == [FrequentTitle("Platform Engineer", 3, 2, 3)]


@pytest.mark.unit
def test_lists_up_to_5_titles_the_most_frequent_first() -> None:
    # Arrange
    offers = [_offer(f"Title {n}") for n in range(6) for _ in range(2)] + [_offer("Title 9")] * 3

    # Act
    titles = frequent_titles(offers)

    # Assert
    assert [t.title for t in titles] == ["Title 9", "Title 0", "Title 1", "Title 2", "Title 3"]
