import asyncio
from typing import Any

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from support.postgres import alembic_config, current_revision

from funnel.core.db import Base

pytestmark = pytest.mark.migrations


def _diff_against_models(connection: Connection) -> list[Any]:
    return list(compare_metadata(MigrationContext.configure(connection), Base.metadata))


async def _schema_diff(database_url: str) -> list[Any]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            return await connection.run_sync(_diff_against_models)
    finally:
        await engine.dispose()


def test_migrations_survive_full_downgrade_and_upgrade(empty_database_url: str) -> None:
    # Arrange
    config = alembic_config(empty_database_url)
    command.upgrade(config, "head")

    # Act
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    # Assert
    head = ScriptDirectory.from_config(config).get_current_head()
    assert current_revision(empty_database_url) == head


def test_migrated_schema_matches_orm_models(empty_database_url: str) -> None:
    # Arrange
    command.upgrade(alembic_config(empty_database_url), "head")

    # Act
    diff = asyncio.run(_schema_diff(empty_database_url))

    # Assert
    assert diff == []
