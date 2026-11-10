"""Offer status rules and duplicate detection.

Source of truth: specs/inbox/inbox.feature.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from http import HTTPStatus
from typing import Final

from funnel.core.exceptions import AppError, DomainError
from funnel.modules.discovery.domain import Feed


class OfferStatus(StrEnum):
    PENDING = "pending"
    DISCARDED = "discarded"
    PROMOTED = "promoted"


class Ats(StrEnum):
    """Applicant tracking systems whose public job boards can be read (no limits stated)."""

    ASHBY = "ashby"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"


# The strictest feed terms (Remotive: at most 4 reads a day) apply to every feed.
FEED_COOLDOWN: Final = timedelta(hours=6)
EXPIRED_REASON: Final = "expired"


@dataclass(frozen=True)
class FeedOffer:
    """An offer as a feed publishes it; `url` is the link its terms ask to keep."""

    title: str
    company: str
    description: str
    url: str


def next_import_at(last_imported_at: datetime) -> datetime:
    return last_imported_at + FEED_COOLDOWN


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


class FeedCooldownError(AppError):
    """The feed was imported too recently: its terms limit how often it may be read."""

    slug = "feed-cooldown"
    title = "Feed imported too recently"
    status = HTTPStatus.TOO_MANY_REQUESTS

    def __init__(self, feed: Feed, allowed_at: datetime, now: datetime) -> None:
        wait = int((allowed_at - now).total_seconds())
        super().__init__(
            f"{feed} can be imported again at {allowed_at.isoformat()}",
            headers={"Retry-After": str(wait)},
        )


class FeedUnavailableError(AppError):
    slug = "feed-unavailable"
    title = "Feed not available"
    status = HTTPStatus.BAD_GATEWAY


class BoardUnavailableError(AppError):
    """The watched company's ATS did not answer, or does not know its board."""

    slug = "board-unavailable"
    title = "Board not available"
    status = HTTPStatus.BAD_GATEWAY


class UnknownJobBoardError(AppError):
    """The job board referenced in the request does not exist (422: the path is valid)."""

    slug = "unknown-job-board"
    title = "Unknown job board"
    status = HTTPStatus.UNPROCESSABLE_CONTENT
