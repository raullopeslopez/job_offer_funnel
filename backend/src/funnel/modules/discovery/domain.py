"""Vocabulary and rules of discovery.

Source of truth: specs/discovery/.
"""

from enum import StrEnum


class WorkMode(StrEnum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
