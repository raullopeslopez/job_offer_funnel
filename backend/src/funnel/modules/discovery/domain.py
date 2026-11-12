"""Vocabulary and rules of discovery.

Source of truth: specs/discovery/.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from http import HTTPStatus
from typing import Final
from urllib.parse import quote

from funnel.core.exceptions import AppError


class WorkMode(StrEnum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


class Syntax(StrEnum):
    """How a job board reads a search."""

    BOOLEAN = "boolean"  # AND, OR, NOT, "quotes" and (parentheses)
    MINUS = "minus"  # OR, "quotes" and -word to exclude
    KEYWORDS = "keywords"  # plain words


class ImportMethod(StrEnum):
    """How the offers of a job board reach the inbox."""

    NONE = "none"  # by hand, with its generated searches
    API = "api"  # imported from its public feed
    RSS = "rss"  # imported from its RSS, read once per search profile title
    EMAIL = "email"  # imported from its job alert emails


class Feed(StrEnum):
    """Public JSON APIs of remote job boards (see docs/fase0.md for their terms)."""

    HIMALAYAS = "himalayas"
    JOBICY = "jobicy"
    REMOTEOK = "remoteok"
    REMOTIVE = "remotive"


class EmailAlert(StrEnum):
    """Job alert emails the app can read, one format each (see docs/fase0.md)."""

    LINKEDIN = "linkedin"


# The strictest feed terms (Remotive: at most 4 reads a day) apply to every feed.
IMPORT_COOLDOWN: Final = timedelta(hours=6)


def next_import_at(last_imported_at: datetime) -> datetime:
    return last_imported_at + IMPORT_COOLDOWN


class FeedTakenError(AppError):
    """Each feed is imported by one job board at most."""

    slug = "feed-taken"
    title = "Feed already imported by another job board"
    status = HTTPStatus.CONFLICT


class EmailAlertTakenError(AppError):
    """Each email alert is imported by one job board at most."""

    slug = "email-alert-taken"
    title = "Email alert already imported by another job board"
    status = HTTPStatus.CONFLICT


# Placeholders of a job board's search URL template.
QUERY_PLACEHOLDER: Final = "query"
LOCATION_PLACEHOLDER: Final = "location"
PLACEHOLDERS: Final = frozenset({QUERY_PLACEHOLDER, LOCATION_PLACEHOLDER})


@dataclass(frozen=True)
class SearchTerms:
    """What a search profile looks for: its words, and where and how the work is done."""

    titles: Sequence[str]  # any of them
    keywords: Sequence[str]  # all of them
    excluded_keywords: Sequence[str]  # none of them
    location: str | None = None
    work_modes: Sequence[WorkMode] = ()  # any of them; none means any


@dataclass(frozen=True)
class GeneratedSearch:
    query: str
    url: str


def build_queries(terms: SearchTerms, syntax: Syntax) -> list[str]:
    """The queries a job board needs: one, or one per title when it has no OR."""
    match syntax:
        case Syntax.BOOLEAN:
            required = [f"AND {_phrase(word)}" for word in terms.keywords]
            excluded = [f"NOT {_phrase(word)}" for word in terms.excluded_keywords]
            return [_join([_any_title(terms.titles), *required, *excluded])]
        case Syntax.MINUS:
            required = [_phrase(word) for word in terms.keywords]
            excluded = [f"-{_phrase(word)}" for word in terms.excluded_keywords]
            return [_join([_any_title(terms.titles), *required, *excluded])]
        case Syntax.KEYWORDS:
            # No operators: exclusions cannot be expressed, so they are left out.
            return [_join([title, *terms.keywords]) for title in terms.titles]


def build_url(template: str, query: str, location: str | None) -> str:
    """Fill the job board's template; without a location, {location} is left empty."""
    return template.replace(f"{{{QUERY_PLACEHOLDER}}}", quote(query, safe="")).replace(
        f"{{{LOCATION_PLACEHOLDER}}}", quote(location or "", safe="")
    )


def _phrase(words: str) -> str:
    # Several words must match together, so they go between quotes.
    return f'"{words}"' if " " in words else words


def _any_title(titles: Sequence[str]) -> str:
    phrases = [_phrase(title) for title in titles]
    return phrases[0] if len(phrases) == 1 else f"({' OR '.join(phrases)})"


def _join(parts: Sequence[str]) -> str:
    return " ".join(parts)
