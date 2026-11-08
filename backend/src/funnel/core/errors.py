"""Application errors and their single mapping to RFC 9457 problem details."""

from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException

PROBLEM_MEDIA_TYPE = "application/problem+json"


class ProblemRead(BaseModel):
    """RFC 9457 problem details, as returned by every error response (for OpenAPI docs)."""

    type: str
    title: str
    status: int
    detail: str | None = None


class AppError(Exception):
    """Base for errors that reach the client. Subclasses set slug, title and status."""

    slug = "internal-error"
    title = "Internal error"
    status = HTTPStatus.INTERNAL_SERVER_ERROR

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


class UnauthorizedError(AppError):
    slug = "unauthorized"
    title = "Missing or invalid credentials"
    status = HTTPStatus.UNAUTHORIZED


@dataclass(frozen=True)
class Problem:
    slug: str
    title: str
    status: int
    detail: str | None = None
    extensions: dict[str, Any] = field(default_factory=dict)

    def to_response(self) -> JSONResponse:
        body: dict[str, Any] = {
            "type": f"/problems/{self.slug}",
            "title": self.title,
            "status": self.status,
        }
        if self.detail is not None:
            body["detail"] = self.detail
        body.update(self.extensions)
        return JSONResponse(
            jsonable_encoder(body), status_code=self.status, media_type=PROBLEM_MEDIA_TYPE
        )


async def _handle_app_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return Problem(exc.slug, exc.title, exc.status, exc.detail).to_response()


async def _handle_validation_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    return Problem(
        slug="validation-error",
        title="Request validation failed",
        status=HTTPStatus.UNPROCESSABLE_CONTENT,
        extensions={"errors": exc.errors()},
    ).to_response()


async def _handle_http_exception(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)
    status = HTTPStatus(exc.status_code)
    return Problem(status.phrase.lower().replace(" ", "-"), status.phrase, status).to_response()


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(HTTPException, _handle_http_exception)
