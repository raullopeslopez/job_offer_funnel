"""Render the OpenAPI schema. `python -m funnel.openapi` writes backend/openapi.json."""

import json
from pathlib import Path

from pydantic import SecretStr

from funnel.core.config import Settings
from funnel.main import create_app

OPENAPI_PATH = Path(__file__).resolve().parents[2] / "openapi.json"


def render_openapi() -> str:
    # Schema generation needs no real database or token.
    settings = Settings(database_url="postgresql+asyncpg://unused", auth_token=SecretStr("unused"))
    schema = create_app(settings).openapi()
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


if __name__ == "__main__":
    OPENAPI_PATH.write_text(render_openapi(), encoding="utf-8", newline="\n")
    print(f"Wrote {OPENAPI_PATH}")
