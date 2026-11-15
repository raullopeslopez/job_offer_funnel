"""The migration that gives every offer already in the inbox its variant key."""

import asyncio
from typing import Any

import asyncpg
import pytest
from alembic import command
from support.postgres import alembic_config, asyncpg_dsn

pytestmark = pytest.mark.migrations

BEFORE = "e6f3b9a2c7d5"
AFTER = "f7a4c1d8e2b6"

DATA_BEFORE = """
INSERT INTO offers (id, url, company, title, duplicate_key, status, created_at) VALUES
    (gen_random_uuid(), 'https://jobs.example/1', 'Acme',
     'Full-Stack Engineer (Backend) - Payments', 'a', 'pending', '2026-03-10 01:00+00'),
    (gen_random_uuid(), 'https://jobs.example/2', 'ACME', 'Senior  Engineer, Backend', 'b',
     'discarded', '2026-03-10 02:00+00'),
    (gen_random_uuid(), 'https://jobs.example/3', 'Globex', '(Senior) Backend Engineer', 'c',
     'pending', '2026-03-10 03:00+00');
"""

VARIANT_KEYS = "SELECT variant_key FROM offers ORDER BY created_at"


async def _run(database_url: str, statement: str) -> list[tuple[Any, ...]]:
    connection = await asyncpg.connect(asyncpg_dsn(database_url))
    try:
        if statement.lstrip().startswith("SELECT"):
            return [tuple(row.values()) for row in await connection.fetch(statement)]
        await connection.execute(statement)
        return []
    finally:
        await connection.close()


def _sql(database_url: str, statement: str) -> list[tuple[Any, ...]]:
    return asyncio.run(_run(database_url, statement))


def test_upgrade_gives_every_offer_its_variant_key(empty_database_url: str) -> None:
    # Arrange
    config = alembic_config(empty_database_url)
    command.upgrade(config, BEFORE)
    _sql(empty_database_url, DATA_BEFORE)

    # Act
    command.upgrade(config, AFTER)

    # Assert
    assert _sql(empty_database_url, VARIANT_KEYS) == [
        ("acme|full-stack engineer",),
        ("acme|senior engineer",),
        ("globex|(senior) backend engineer",),
    ]
