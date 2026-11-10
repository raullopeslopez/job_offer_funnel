"""The migration that moves the source of imported offers from their feed to a job board."""

import asyncio
from typing import Any

import asyncpg
import pytest
from alembic import command
from support.postgres import alembic_config, asyncpg_dsn

pytestmark = pytest.mark.migrations

BEFORE = "413434bd934b"
AFTER = "a7d2f4c91b3e"

# A job board that exists under another case, a feed without job board, an offer added by
# hand and a job board that is not a feed.
DATA_BEFORE = """
INSERT INTO job_boards (id, name, search_url_template, syntax) VALUES
    (gen_random_uuid(), 'remote ok', 'https://remoteok.com/?q={query}', 'keywords'),
    (gen_random_uuid(), 'LinkedIn', 'https://linkedin.com/?q={query}', 'boolean');
INSERT INTO feed_imports (feed, last_imported_at) VALUES
    ('remoteok', '2026-03-10 04:00+00'), ('jobicy', '2026-03-10 05:00+00');
INSERT INTO offers (id, url, company, title, description, duplicate_key, status, feed) VALUES
    (gen_random_uuid(), 'https://remoteok.com/1', 'Acme', 'From Remote OK', '', 'a', 'pending',
     'remoteok'),
    (gen_random_uuid(), 'https://jobicy.com/1', 'Acme', 'From Jobicy', 'Python', 'b', 'pending',
     'jobicy');
INSERT INTO offers (id, url, company, title, duplicate_key, status, job_board_id)
    SELECT gen_random_uuid(), 'https://linkedin.com/1', 'Acme', 'By hand', 'c', 'pending', id
    FROM job_boards WHERE name = 'LinkedIn';
"""

JOB_BOARDS = (
    "SELECT name, import_method, feed, last_imported_at IS NOT NULL AS imported "
    "FROM job_boards ORDER BY lower(name)"
)
OFFER_JOB_BOARDS = (
    "SELECT offers.title, job_boards.name FROM offers "
    "LEFT JOIN job_boards ON job_boards.id = offers.job_board_id ORDER BY offers.title"
)
OFFER_FEEDS = (
    "SELECT offers.title, offers.feed, job_boards.name FROM offers "
    "LEFT JOIN job_boards ON job_boards.id = offers.job_board_id ORDER BY offers.title"
)
FEED_IMPORTS = "SELECT feed FROM feed_imports ORDER BY feed"


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


@pytest.fixture
def config_with_feed_data(empty_database_url: str) -> Any:
    config = alembic_config(empty_database_url)
    command.upgrade(config, BEFORE)
    _sql(empty_database_url, DATA_BEFORE)
    return config


def test_upgrade_moves_the_feed_of_offers_and_imports_to_job_boards(
    empty_database_url: str, config_with_feed_data: Any
) -> None:
    # Act
    command.upgrade(config_with_feed_data, AFTER)

    # Assert
    assert _sql(empty_database_url, JOB_BOARDS) == [
        ("Jobicy", "api", "jobicy", True),
        ("LinkedIn", "none", None, False),
        ("remote ok", "api", "remoteok", True),
    ]
    assert _sql(empty_database_url, OFFER_JOB_BOARDS) == [
        ("By hand", "LinkedIn"),
        ("From Jobicy", "Jobicy"),
        ("From Remote OK", "remote ok"),
    ]


def test_downgrade_gives_imported_offers_their_feed_back(
    empty_database_url: str, config_with_feed_data: Any
) -> None:
    # Arrange
    command.upgrade(config_with_feed_data, AFTER)

    # Act
    command.downgrade(config_with_feed_data, BEFORE)

    # Assert
    assert _sql(empty_database_url, OFFER_FEEDS) == [
        ("By hand", None, "LinkedIn"),
        ("From Jobicy", "jobicy", None),
        ("From Remote OK", "remoteok", None),
    ]
    assert _sql(empty_database_url, FEED_IMPORTS) == [("jobicy",), ("remoteok",)]
