"""Offer status rules and duplicate detection.

Source of truth: specs/inbox/inbox.feature.
"""

from collections.abc import Mapping
from enum import StrEnum
from http import HTTPStatus
from typing import Final

from funnel.core.exceptions import AppError, DomainError


class OfferStatus(StrEnum):
    PENDING = "pending"
    DISCARDED = "discarded"
    PROMOTED = "promoted"


class Feed(StrEnum):
    """Remote job boards with a public JSON API (see docs/fase0.md for their terms)."""

    HIMALAYAS = "himalayas"
    JOBICY = "jobicy"
    REMOTEOK = "remoteok"
    REMOTIVE = "remotive"


class OfferAction(StrEnum):
    DISCARD = "discard"
    RESTORE = "restore"
    PROMOTE = "promote"


# The only status each action can start from, and the status it leads to.
ACTIONS: Final[Mapping[OfferAction, tuple[OfferStatus, OfferStatus]]] = {
    OfferAction.DISCARD: (OfferStatus.PENDING, OfferStatus.DISCARDED),
    OfferAction.RESTORE: (OfferStatus.DISCARDED, OfferStatus.PENDING),
    OfferAction.PROMOTE: (OfferStatus.PENDING, OfferStatus.PROMOTED),
}


def next_status(current: OfferStatus, action: OfferAction) -> OfferStatus:
    required, result = ACTIONS[action]
    if current is not required:
        raise InvalidOfferStatusError(f"Cannot {action} an offer that is {current}")
    return result


def duplicate_key(company: str, title: str) -> str:
    """Company and title ignoring case and extra spaces: equal keys mean the same offer."""
    return "|".join(" ".join(text.split()).casefold() for text in (company, title))


class InvalidOfferStatusError(DomainError):
    slug = "invalid-offer-status"
    title = "Invalid offer status"
    status = HTTPStatus.CONFLICT


class UnknownSearchProfileError(AppError):
    """The search profile referenced in the request does not exist."""

    slug = "unknown-search-profile"
    title = "Unknown search profile"
    status = HTTPStatus.UNPROCESSABLE_CONTENT


class FeedCooldownError(AppError):
    """The feed was imported too recently: its terms limit how often it may be read."""

    slug = "feed-cooldown"
    title = "Feed imported too recently"
    status = HTTPStatus.TOO_MANY_REQUESTS


class FeedUnavailableError(AppError):
    slug = "feed-unavailable"
    title = "Feed not available"
    status = HTTPStatus.BAD_GATEWAY


class UnknownJobBoardError(AppError):
    """The job board referenced in the request does not exist (422: the path is valid)."""

    slug = "unknown-job-board"
    title = "Unknown job board"
    status = HTTPStatus.UNPROCESSABLE_CONTENT
