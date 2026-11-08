"""Persist test data directly, for Given steps that need state no endpoint can create yet."""

import asyncio
from datetime import date
from uuid import UUID, uuid7

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from funnel.core.db import Base
from funnel.modules.applications.domain import Outcome, Stage
from funnel.modules.applications.models import ApplicationRow, TransitionRow

DEFAULT_ENTERED_ON = date(2026, 3, 1)


async def _insert(database_url: str, rows: list[Base]) -> None:
    engine = create_async_engine(database_url)
    try:
        async with AsyncSession(engine) as session, session.begin():
            session.add_all(rows)
    finally:
        await engine.dispose()


def make_application(
    database_url: str,
    *,
    stage: Stage,
    outcome: Outcome | None = None,
    entered_on: date = DEFAULT_ENTERED_ON,
) -> UUID:
    """An application that entered `stage` on `entered_on`, closed with `outcome` if given."""
    application_id = uuid7()
    rows: list[Base] = [
        ApplicationRow(id=application_id, stage=stage, outcome=outcome),
        TransitionRow(
            application_id=application_id, from_stage=None, to_stage=stage, occurred_on=entered_on
        ),
    ]
    if outcome is not None:
        rows.append(
            TransitionRow(
                application_id=application_id,
                from_stage=stage,
                to_stage=stage,
                outcome=outcome,
                occurred_on=entered_on,
            )
        )
    asyncio.run(_insert(database_url, rows))
    return application_id
