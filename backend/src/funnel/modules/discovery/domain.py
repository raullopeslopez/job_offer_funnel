"""Vocabulary and rules of discovery.

Source of truth: specs/discovery/.
"""

from enum import StrEnum
from typing import Final


class WorkMode(StrEnum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


class Syntax(StrEnum):
    """How a job board reads a search."""

    BOOLEAN = "boolean"  # AND, OR, NOT, "quotes" and (parentheses)
    KEYWORDS = "keywords"  # plain words


# Placeholders of a job board's search URL template.
QUERY_PLACEHOLDER: Final = "query"
LOCATION_PLACEHOLDER: Final = "location"
PLACEHOLDERS: Final = frozenset({QUERY_PLACEHOLDER, LOCATION_PLACEHOLDER})
