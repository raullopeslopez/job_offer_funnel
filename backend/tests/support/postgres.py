"""Postgres helpers for tests: database creation, cleanup and Alembic config."""

import asyncio
from pathlib import Path

import asyncpg
from alembic.config import Config
from sqlalchemy.engine import make_url

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def database_url_for(server_url: str, database: str) -> str:
    return make_url(server_url).set(database=database).render_as_string(hide_password=False)


def asyncpg_dsn(url: str) -> str:
    return make_url(url).set(drivername="postgresql").render_as_string(hide_password=False)


def alembic_config(database_url: str) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


async def _execute(server_url: str, statement: str) -> None:
    connection = await asyncpg.connect(asyncpg_dsn(server_url))
    try:
        await connection.execute(statement)
    finally:
        await connection.close()


def create_database(server_url: str, name: str, template: str = "template0") -> str:
    """(Re)create `name` as a copy of `template` and return its URL."""
    asyncio.run(_execute(server_url, f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    asyncio.run(_execute(server_url, f'CREATE DATABASE "{name}" TEMPLATE "{template}"'))
    return database_url_for(server_url, name)


async def _truncate_all_tables(database_url: str) -> None:
    connection = await asyncpg.connect(asyncpg_dsn(database_url))
    try:
        tables = await connection.fetch(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
        )
        if tables:
            names = ", ".join(f'"{row["tablename"]}"' for row in tables)
            await connection.execute(f"TRUNCATE {names} RESTART IDENTITY CASCADE")
    finally:
        await connection.close()


def truncate_all_tables(database_url: str) -> None:
    asyncio.run(_truncate_all_tables(database_url))


async def _fetch_revision(database_url: str) -> str | None:
    connection = await asyncpg.connect(asyncpg_dsn(database_url))
    try:
        revision: str | None = await connection.fetchval(
            "SELECT version_num FROM alembic_version LIMIT 1"
        )
        return revision
    finally:
        await connection.close()


def current_revision(database_url: str) -> str | None:
    return asyncio.run(_fetch_revision(database_url))
