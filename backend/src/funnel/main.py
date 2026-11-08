from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from http import HTTPStatus

from fastapi import APIRouter, Depends, FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from funnel.core import health
from funnel.core.auth import require_token
from funnel.core.config import Settings
from funnel.core.errors import ProblemRead, register_error_handlers
from funnel.core.logging import configure_logging
from funnel.modules.applications import router as applications


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    engine = create_async_engine(settings.database_url)
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
    yield
    await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    """App factory. Without arguments, settings come from the environment."""
    settings = settings or Settings()  # type: ignore[call-arg]  # filled from env vars
    configure_logging(settings.log_level)

    app = FastAPI(title="Job Offer Funnel", version="0.1.0", lifespan=_lifespan)
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
                "model": ProblemRead,
                "description": "Invalid request",
            },
        },
    )
    api.include_router(applications.router)

    app.include_router(health.router)
    app.include_router(api)
    return app
