"""API for the frontend E2E tests (Playwright), against its own throwaway Postgres.

Run from `backend/tests` with `uv run python -m support.e2e_server`; Playwright starts it.
Adds `POST /e2e/reset` (empties every table between scenarios) to this test app only:
it never exists in the real API.
"""

import os
from http import HTTPStatus

import uvicorn
from alembic import command
from pydantic import SecretStr
from testcontainers.community.postgres import PostgresContainer

from funnel.core.config import Settings
from funnel.main import create_app
from support.postgres import alembic_config, truncate_all_tables

POSTGRES_IMAGE = "postgres:17-alpine"
PORT = int(os.environ.get("E2E_API_PORT", "8001"))
TOKEN = os.environ.get("E2E_TOKEN", "e2e-token")


def main() -> None:
    with PostgresContainer(POSTGRES_IMAGE, driver="asyncpg") as container:
        database_url = container.get_connection_url()
        command.upgrade(alembic_config(database_url), "head")

        app = create_app(Settings(database_url=database_url, auth_token=SecretStr(TOKEN)))

        @app.post("/e2e/reset", status_code=HTTPStatus.NO_CONTENT, include_in_schema=False)
        def reset() -> None:
            truncate_all_tables(database_url)

        uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
