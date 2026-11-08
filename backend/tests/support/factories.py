"""Persist test data directly, for Given steps that need state no endpoint can create yet."""

import asyncio
from dataclasses import dataclass
from datetime import date
from uuid import UUID, uuid7

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from funnel.core.db import Base
from funnel.modules.applications.domain import Channel, Outcome, Priority, Stage
from funnel.modules.applications.models import ApplicationRow, TransitionRow
from funnel.modules.companies.models import CompanyRow

DEFAULT_ENTERED_ON = date(2026, 3, 1)


@dataclass(frozen=True)
class ApplicationDetails:
    """The descriptive fields of an application; the defaults fill the required ones."""

    company_id: UUID | None = None
    role: str = "Backend Engineer"
    channel: Channel = Channel.PORTAL
    priority: Priority | None = None
    url: str | None = None
    notes: str | None = None


async def _insert(database_url: str, rows: list[Base]) -> None:
    engine = create_async_engine(database_url)
    try:
        async with AsyncSession(engine) as session, session.begin():
            for row in rows:
                # One flush per row keeps the insert order (and so created_at) as given.
                session.add(row)
                await session.flush()
    finally:
        await engine.dispose()


def make_application(
    database_url: str,
    *,
    stage: Stage,
    outcome: Outcome | None = None,
    entered_on: date = DEFAULT_ENTERED_ON,
    details: ApplicationDetails = ApplicationDetails(),  # noqa: B008  # frozen, so shared safely
) -> UUID:
    """An application that entered `stage` on `entered_on`, closed with `outcome` if given.

    Without a `company_id` in `details`, a new company is created for it.
    """
    rows: list[Base] = []
    company_id = details.company_id
    if company_id is None:
        company_id = uuid7()
        rows.append(CompanyRow(id=company_id, name=f"Company {company_id}"))
    application_id = uuid7()
    rows.append(
        ApplicationRow(
            id=application_id,
            company_id=company_id,
            role=details.role,
            channel=details.channel,
            priority=details.priority,
            url=details.url,
            notes=details.notes,
            stage=stage,
            outcome=outcome,
        )
    )
    rows.append(
        TransitionRow(
            application_id=application_id, from_stage=None, to_stage=stage, occurred_on=entered_on
        )
    )
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
