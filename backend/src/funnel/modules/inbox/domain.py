"""Offer status rules and duplicate detection.

Source of truth: specs/inbox/inbox.feature.
"""

from enum import StrEnum
from http import HTTPStatus

from funnel.core.exceptions import AppError, DomainError


class OfferStatus(StrEnum):
    PENDING = "pending"
    DISCARDED = "discarded"
    PROMOTED = "promoted"


class InvalidOfferStatusError(DomainError):
    slug = "invalid-offer-status"
    title = "Invalid offer status"
    status = HTTPStatus.CONFLICT


class UnknownJobBoardError(AppError):
    """The job board referenced in the request does not exist (422: the path is valid)."""

    slug = "unknown-job-board"
    title = "Unknown job board"
    status = HTTPStatus.UNPROCESSABLE_CONTENT
