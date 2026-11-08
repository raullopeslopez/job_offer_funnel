"""The real app plus probe routes, to test core behaviour without any module or database."""

from fastapi import Depends, FastAPI
from pydantic import SecretStr

from funnel.core.auth import require_token
from funnel.core.config import Settings
from funnel.core.errors import AppError, DomainError, NotFoundError, UnauthorizedError
from funnel.main import create_app

PROBE_TOKEN = "probe-token"

RAISABLE_ERRORS: dict[str, type[AppError]] = {
    "domain": DomainError,
    "not-found": NotFoundError,
    "unauthorized": UnauthorizedError,
}


def build_probe_app() -> FastAPI:
    # The lifespan (database engine) only runs inside `with TestClient(...)`; unit tests skip it.
    settings = Settings(
        database_url="postgresql+asyncpg://unused", auth_token=SecretStr(PROBE_TOKEN)
    )
    app = create_app(settings)

    @app.get("/probe/protected", dependencies=[Depends(require_token)])
    async def read_protected() -> dict[str, str]:
        return {"access": "granted"}

    @app.get("/probe/errors/{name}")
    async def raise_error(name: str) -> None:
        raise RAISABLE_ERRORS[name](detail=f"probe {name}")

    @app.get("/probe/items/{item_id}")
    async def read_item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    return app
