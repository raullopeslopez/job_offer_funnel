"""The migration that reads the HTML character references of the offers already imported."""

import asyncio
from typing import Any

import asyncpg
import pytest
from alembic import command
from support.postgres import alembic_config, asyncpg_dsn

pytestmark = pytest.mark.migrations

BEFORE = "d3a8b6e1f2c4"
AFTER = "e6f3b9a2c7d5"

# An imported offer with references, one with a plain "&", one whose fixed text is the
# same offer as another one, and one added by hand (no description) typed with a reference.
DATA_BEFORE = """
INSERT INTO offers (id, url, company, title, description, duplicate_key, status, created_at)
VALUES
    (gen_random_uuid(), 'https://jobicy.com/1', 'Quest &#038; Solutions', 'R&amp;D Engineer', '',
     'quest &#038; solutions|r&amp;d engineer', 'pending', '2026-03-10 01:00+00'),
    (gen_random_uuid(), 'https://jobicy.com/2', 'Marks & Co', 'Backend Engineer', '',
     'marks & co|backend engineer', 'pending', '2026-03-10 02:00+00'),
    (gen_random_uuid(), 'https://jobicy.com/3', 'Marks &amp; Co', 'Backend Engineer', '',
     'marks &amp; co|backend engineer', 'pending', '2026-03-10 03:00+00'),
    (gen_random_uuid(), 'https://example.com/4', 'By &amp; Hand', 'Typed', NULL,
     'by &amp; hand|typed', 'pending', '2026-03-10 04:00+00');
"""

OFFERS = "SELECT company, title, duplicate_key FROM offers ORDER BY created_at"


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


def test_upgrade_reads_the_references_of_imported_offers(empty_database_url: str) -> None:
    # Arrange
    config = alembic_config(empty_database_url)
    command.upgrade(config, BEFORE)
    _sql(empty_database_url, DATA_BEFORE)

    # Act
    command.upgrade(config, AFTER)

    # Assert
    assert _sql(empty_database_url, OFFERS) == [
        ("Quest & Solutions", "R&D Engineer", "quest & solutions|r&d engineer"),
        ("Marks & Co", "Backend Engineer", "marks & co|backend engineer"),
        ("Marks & Co", "Backend Engineer", "marks &amp; co|backend engineer"),
        ("By &amp; Hand", "Typed", "by &amp; hand|typed"),
    ]
