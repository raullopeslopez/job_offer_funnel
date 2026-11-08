import pytest

from funnel.modules.discovery.domain import SearchTerms, Syntax, build_queries, build_url

pytestmark = pytest.mark.unit

FULL = SearchTerms(
    titles=["Backend Engineer", "Python Developer"],
    keywords=["Python", "PostgreSQL"],
    excluded_keywords=["PHP", "Project Manager"],
)
SINGLE_TITLE = SearchTerms(titles=["Backend Engineer"], keywords=[], excluded_keywords=[])
ONE_WORD_TITLES = SearchTerms(titles=["Backend", "Platform"], keywords=[], excluded_keywords=[])


@pytest.mark.parametrize(
    ("terms", "syntax", "expected"),
    [
        pytest.param(
            FULL,
            Syntax.BOOLEAN,
            [
                '("Backend Engineer" OR "Python Developer") AND Python AND PostgreSQL'
                ' NOT PHP NOT "Project Manager"'
            ],
            id="boolean",
        ),
        pytest.param(
            FULL,
            Syntax.MINUS,
            [
                '("Backend Engineer" OR "Python Developer") Python PostgreSQL'
                ' -PHP -"Project Manager"'
            ],
            id="minus",
        ),
        pytest.param(
            FULL,
            Syntax.KEYWORDS,
            ["Backend Engineer Python PostgreSQL", "Python Developer Python PostgreSQL"],
            id="keywords-one-per-title-without-exclusions",
        ),
        pytest.param(SINGLE_TITLE, Syntax.BOOLEAN, ['"Backend Engineer"'], id="boolean-single"),
        pytest.param(SINGLE_TITLE, Syntax.MINUS, ['"Backend Engineer"'], id="minus-single"),
        pytest.param(SINGLE_TITLE, Syntax.KEYWORDS, ["Backend Engineer"], id="keywords-single"),
        pytest.param(
            ONE_WORD_TITLES, Syntax.BOOLEAN, ["(Backend OR Platform)"], id="one-word-unquoted"
        ),
    ],
)
def test_build_queries(terms: SearchTerms, syntax: Syntax, expected: list[str]) -> None:
    # Act
    queries = build_queries(terms, syntax)

    # Assert
    assert queries == expected


@pytest.mark.parametrize(
    ("template", "location", "expected"),
    [
        pytest.param(
            "https://jobs.example/s?q={query}&l={location}",
            "Kuala Lumpur",
            "https://jobs.example/s?q=%22Backend%20Engineer%22%20OR%20x&l=Kuala%20Lumpur",
            id="encodes-query-and-location",
        ),
        pytest.param(
            "https://jobs.example/s?q={query}&l={location}",
            None,
            "https://jobs.example/s?q=%22Backend%20Engineer%22%20OR%20x&l=",
            id="no-location-leaves-it-empty",
        ),
        pytest.param(
            "https://jobs.example/s?q={query}",
            "Madrid",
            "https://jobs.example/s?q=%22Backend%20Engineer%22%20OR%20x",
            id="template-without-location",
        ),
    ],
)
def test_build_url(template: str, location: str | None, expected: str) -> None:
    # Act
    url = build_url(template, '"Backend Engineer" OR x', location)

    # Assert
    assert url == expected
