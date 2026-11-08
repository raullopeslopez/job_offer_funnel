"""Controlled errors. Plain Python on purpose: the domain raises them without depending on HTTP.

Each subclass is a stable `type` slug of the error contract (see core/errors.py);
renaming a slug is a breaking change.
"""

from collections.abc import Mapping
from http import HTTPStatus
from typing import ClassVar


class AppError(Exception):
    """Base for controlled errors. Subclasses set slug, title and status."""

    slug: ClassVar[str] = "internal-error"
    title: ClassVar[str] = "Internal error"
    status: ClassVar[HTTPStatus] = HTTPStatus.INTERNAL_SERVER_ERROR
    headers: ClassVar[Mapping[str, str]] = {}

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.title)
        self.detail = detail


class DomainError(AppError):
    """Base for business rule violations."""

    slug = "domain-error"
    title = "Business rule violated"
    status = HTTPStatus.CONFLICT


class NotFoundError(AppError):
    slug = "not-found"
    title = "Resource not found"
    status = HTTPStatus.NOT_FOUND


class AlreadyExistsError(AppError):
    slug = "already-exists"
    title = "Resource already exists"
    status = HTTPStatus.CONFLICT


class InUseError(AppError):
    """Other resources still reference this one, so it cannot be deleted."""

    slug = "in-use"
    title = "Resource in use"
    status = HTTPStatus.CONFLICT


class UnauthorizedError(AppError):
    slug = "unauthorized"
    title = "Missing or invalid credentials"
    status = HTTPStatus.UNAUTHORIZED
    headers = {"WWW-Authenticate": "Bearer"}
