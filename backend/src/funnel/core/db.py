from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy import MetaData
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from funnel.core.exceptions import AlreadyExistsError, InUseError

# Postgres error code for a row still referenced by a foreign key.
_FOREIGN_KEY_VIOLATION = "23503"

# Deterministic constraint names keep Alembic migrations reversible.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """One session per request: commit on success, rollback on error.

    Services and repositories never commit.
    """
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def flush_checking_unique(session: AsyncSession, unique_index: str, detail: str) -> None:
    """Flush now, so a duplicate surfaces here as `already-exists` and not at commit.

    Uniqueness is enforced by a UNIQUE index, never by an "exists?" check in Python.
    Build `detail` before calling: after a failed flush the rows cannot be loaded.
    """
    try:
        await session.flush()
    except IntegrityError as error:
        if unique_index in str(error.orig):
            raise AlreadyExistsError(detail) from error
        raise


async def flush_checking_references(session: AsyncSession, detail: str) -> None:
    """Flush a delete now, so a row still referenced (ON DELETE RESTRICT) is `in-use`.

    Build `detail` before calling: after a failed flush the rows cannot be loaded.
    """
    try:
        await session.flush()
    except IntegrityError as error:
        if getattr(error.orig, "sqlstate", None) == _FOREIGN_KEY_VIOLATION:
            raise InUseError(detail) from error
        raise
