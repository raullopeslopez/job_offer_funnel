from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from http import HTTPStatus
from importlib.metadata import version

from fastapi import APIRouter, Depends, FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from funnel.core import health
from funnel.core.auth import require_token
from funnel.core.config import Settings
from funnel.core.errors import ProblemRead, ValidationProblemRead, register_error_handlers
from funnel.core.logging import configure_logging
from funnel.modules.applications import router as applications
from funnel.modules.companies import router as companies
from funnel.modules.discovery import router as discovery
from funnel.modules.inbox import router as inbox
from funnel.modules.metrics import router as metrics


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    # No JIT: the filter's expressions make the planner overestimate the cost, and Postgres
    # spent ~2 s compiling them on every inbox read, against ~0.1 s running the query. Set
    # on the connection, so it holds on any Postgres; behind a transaction pooler that
    # rejects startup parameters (PgBouncer), use SET LOCAL per transaction instead.
    engine = create_async_engine(
        settings.database_url, connect_args={"server_settings": {"jit": "off"}}
    )
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
    yield
    await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    """App factory. Without arguments, settings come from the environment."""
    settings = settings or Settings()  # type: ignore[call-arg]  # filled from env vars
    configure_logging(settings.log_level)

    # Single source of the version: backend/pyproject.toml.
    app = FastAPI(title="Job Offer Funnel", version=version("funnel"), lifespan=_lifespan)
    app.state.settings = settings
    register_error_handlers(app)

    api = APIRouter(
        prefix="/api/v1",
        dependencies=[Depends(require_token)],
        responses={
            HTTPStatus.UNAUTHORIZED: {
                "model": ProblemRead,
                "description": "Missing or invalid token",
            },
            HTTPStatus.UNPROCESSABLE_CONTENT: {
                "model": ValidationProblemRead,
                "description": "Invalid request (`validation-error`)",
            },
        },
    )
    api.include_router(applications.router)
    api.include_router(companies.router)
    api.include_router(discovery.router)
    api.include_router(inbox.router)
    api.include_router(metrics.router)

    app.include_router(health.router)
    app.include_router(api)
    return app
