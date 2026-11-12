"""Offer status rules, duplicate detection and what a reading of an offer may keep.

Source of truth: specs/inbox/inbox.feature and specs/inbox/offer_readings.feature.
"""

import html
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from http import HTTPStatus
from typing import Final

from funnel.core.exceptions import AppError, DomainError
from funnel.modules.discovery.domain import WorkMode


class OfferStatus(StrEnum):
    PENDING = "pending"
    DISCARDED = "discarded"
    PROMOTED = "promoted"


class Ats(StrEnum):
    """Applicant tracking systems whose public job boards can be read (no limits stated)."""

    ASHBY = "ashby"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"


EXPIRED_REASON: Final = "expired"


@dataclass(frozen=True)
class FeedOffer:
    """An offer as a feed publishes it; `url` is the link its terms ask to keep."""

    title: str
    company: str
    description: str
    url: str


# Offers read per request: the offer reader's plan allows about this many a minute.
READING_BATCH_SIZE: Final = 5

_TAG: Final = re.compile(r"<[^>]+>")


def plain_text(description: str) -> str:
    """The description as the text a person reads: no tags, entities or extra spaces."""
    return " ".join(html.unescape(_TAG.sub(" ", description)).split())


@dataclass(frozen=True)
class OfferText:
    """What the offer reader is given; `description` is plain text."""

    title: str
    company: str
    description: str


@dataclass(frozen=True)
class Reading:
    """What a description says; None is what it does not say."""

    work_mode: WorkMode | None = None
    work_mode_evidence: str | None = None
    admits_location: bool | None = None
    admits_location_evidence: str | None = None
    stable: bool | None = None
    stable_evidence: str | None = None


def _quoted(evidence: str | None, text: str) -> str | None:
    """The evidence, if the text says it letter for letter (spaces aside)."""
    quote = " ".join((evidence or "").split())
    return quote if quote and quote in text else None


def supported(answer: Reading, text: str, *, asked_location: bool) -> Reading:
    """Only the answers whose evidence is in the text: the reader cannot make one up."""
    work_mode = _quoted(answer.work_mode_evidence, text)
    admits = _quoted(answer.admits_location_evidence, text) if asked_location else None
    stable = _quoted(answer.stable_evidence, text)
    return Reading(
        work_mode=answer.work_mode if work_mode else None,
        work_mode_evidence=work_mode if answer.work_mode is not None else None,
        admits_location=answer.admits_location if admits else None,
        admits_location_evidence=admits if answer.admits_location is not None else None,
        stable=answer.stable if stable else None,
        stable_evidence=stable if answer.stable is not None else None,
    )


class OfferReaderError(Exception):
    """The offer reader did not answer for an offer, or answered something unusable."""


class OfferReaderUnavailableError(AppError):
    """No offer reader is configured, so nothing can be read."""

    slug = "offer-reader-unavailable"
    title = "Offer reader not available"
    status = HTTPStatus.SERVICE_UNAVAILABLE


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


class JobBoardNotImportedError(DomainError):
    """Only a job board with an import method can be imported."""

    slug = "job-board-not-imported"
    title = "Job board not imported"
    status = HTTPStatus.CONFLICT


class FeedCooldownError(AppError):
    """The feed was imported too recently: its terms limit how often it may be read."""

    slug = "feed-cooldown"
    title = "Feed imported too recently"
    status = HTTPStatus.TOO_MANY_REQUESTS

    def __init__(self, job_board: str, allowed_at: datetime, now: datetime) -> None:
        wait = int((allowed_at - now).total_seconds())
        super().__init__(
            f"{job_board} can be imported again at {allowed_at.isoformat()}",
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


class ImportedByEmailError(DomainError):
    """A job board imported from its email alerts is imported when each alert arrives."""

    slug = "job-board-imported-by-email"
    title = "Job board imported from its email alerts"
    status = HTTPStatus.CONFLICT


class UnsupportedAlertError(AppError):
    """The email does not come from a job alert the app can read."""

    slug = "unsupported-alert"
    title = "Unsupported alert"
    status = HTTPStatus.UNPROCESSABLE_CONTENT


class EmailAlertNotImportedError(DomainError):
    """No job board imports the email alert, so its offers would have no source."""

    slug = "email-alert-not-imported"
    title = "No job board imports this email alert"
    status = HTTPStatus.CONFLICT


class UnknownJobBoardError(AppError):
    """The job board referenced in the request does not exist (422: the path is valid)."""

    slug = "unknown-job-board"
    title = "Unknown job board"
    status = HTTPStatus.UNPROCESSABLE_CONTENT
