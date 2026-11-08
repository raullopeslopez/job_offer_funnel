from collections.abc import Iterator

import pytest
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute, iter_route_contexts
from pydantic import SecretStr

from funnel.core.config import Settings
from funnel.core.db import get_session
from funnel.main import create_app


def _session_dependencies(dependant: Dependant) -> Iterator[Dependant]:
    for dependency in dependant.dependencies:
        if dependency.call is get_session:
            yield dependency
        yield from _session_dependencies(dependency)


def _session_scopes() -> list[pytest.ParameterSet]:
    # No database needed: the app only connects in its lifespan.
    settings = Settings(
        database_url="postgresql+asyncpg://unused/unused", auth_token=SecretStr("t")
    )
    contexts = iter_route_contexts(create_app(settings).routes)
    return [
        pytest.param(dependency.scope, id=f"{' '.join(sorted(route.methods or ()))} {context.path}")
        for context in contexts
        if isinstance(route := context.original_route, APIRoute)
        for dependency in _session_dependencies(route.dependant)
    ]


@pytest.mark.unit
@pytest.mark.parametrize("scope", _session_scopes())
def test_session_commits_before_the_response_is_sent(scope: str | None) -> None:
    # Assert: with the default scope ("request") the commit runs after the response, so a
    # client could read stale data right after a write, or get a 2xx for a failed commit.
    assert scope == "function"
