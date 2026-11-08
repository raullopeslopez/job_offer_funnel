"""Single-user auth: a fixed bearer token from config."""

import secrets
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from funnel.core.config import Settings
from funnel.core.errors import UnauthorizedError

_bearer = HTTPBearer(auto_error=False)


async def require_token(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> None:
    settings: Settings = request.app.state.settings
    expected = settings.auth_token.get_secret_value()
    if credentials is None or not secrets.compare_digest(credentials.credentials, expected):
        raise UnauthorizedError
