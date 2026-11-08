"""Error contract: every error response is RFC 9457 problem details.

- Controlled errors are `AppError` subclasses: each one is a stable `type` slug that
  clients may rely on. Renaming a slug is a breaking change.
- Anything else is unexpected: a generic 500 that never leaks internals; the
  traceback goes to the logs.
- `title` and `detail` are English, human-readable and never parsed by clients.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException

from funnel.core.exceptions import AppError

PROBLEM_MEDIA_TYPE = "application/problem+json"

_logger = structlog.get_logger(__name__)


class ProblemRead(BaseModel):
    """Problem details returned by every error response."""

    type: str
    title: str
    status: int
    detail: str | None = None


class FieldErrorRead(BaseModel):
    field: str
    message: str


class ValidationProblemRead(ProblemRead):
    """Problem details for invalid requests, with one entry per invalid field."""

    errors: list[FieldErrorRead]


@dataclass(frozen=True)
class Problem:
    slug: str
    title: str
    status: int
    detail: str | None = None
    extensions: Mapping[str, Any] = field(default_factory=dict)

    def to_response(self, headers: Mapping[str, str] | None = None) -> JSONResponse:
        body: dict[str, Any] = {
            "type": f"/problems/{self.slug}",
            "title": self.title,
            "status": self.status,
        }
        if self.detail is not None:
            body["detail"] = self.detail
        body.update(self.extensions)
        return JSONResponse(
            jsonable_encoder(body),
            status_code=self.status,
            headers=dict(headers or {}),
            media_type=PROBLEM_MEDIA_TYPE,
        )


def _field_errors(exc: RequestValidationError) -> list[dict[str, str]]:
    # Own stable shape instead of Pydantic's internals (codes, echoed input).
    return [
        {"field": ".".join(str(part) for part in error["loc"]), "message": error["msg"]}
        for error in exc.errors()
    ]


async def _handle_app_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    problem = Problem(exc.slug, exc.title, exc.status, exc.detail)
    return problem.to_response(exc.headers)


async def _handle_validation_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    return Problem(
        slug="validation-error",
        title="Request validation failed",
        status=HTTPStatus.UNPROCESSABLE_CONTENT,
        extensions={"errors": _field_errors(exc)},
    ).to_response()


async def _handle_http_exception(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)
    status = HTTPStatus(exc.status_code)
    return Problem(status.phrase.lower().replace(" ", "-"), status.phrase, status).to_response()


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    _logger.error("unexpected_error", method=request.method, path=request.url.path, exc_info=exc)
    return Problem(
        slug="internal-error",
        title="Internal error",
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred.",
    ).to_response()


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(HTTPException, _handle_http_exception)
    app.add_exception_handler(Exception, _handle_unexpected_error)
