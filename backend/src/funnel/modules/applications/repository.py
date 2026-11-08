from collections.abc import Mapping
from uuid import UUID

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from funnel.core.pagination import PageParams
from funnel.modules.applications.domain import Application, Transition, UnknownCompanyError
from funnel.modules.applications.models import COMPANY_FOREIGN_KEY, ApplicationRow, TransitionRow
from funnel.modules.applications.schemas import ApplicationFilters


class ApplicationRepository:
    """Maps ORM rows to domain objects for the state machine. Never commits: the request
    session does."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, row: ApplicationRow, first: Transition) -> ApplicationRow:
        self._session.add(row)
        await self._flush_checking_company()
        self._session.add(_transition_row(row.id, first))
        await self._session.flush()
        await self._session.refresh(row)  # loads created_at, set by the database
        return row

    async def get(self, application_id: UUID) -> Application | None:
        row = await self._session.get(ApplicationRow, application_id)
        if row is None:
            return None
        last_transition_on = await self._session.scalar(
            select(func.max(TransitionRow.occurred_on)).where(
                TransitionRow.application_id == application_id
            )
        )
        return Application(
            id=row.id, stage=row.stage, outcome=row.outcome, last_transition_on=last_transition_on
        )

    async def get_row(self, application_id: UUID) -> ApplicationRow | None:
        return await self._session.get(ApplicationRow, application_id)

    async def update(self, row: ApplicationRow, changes: Mapping[str, object]) -> ApplicationRow:
        for name, value in changes.items():
            setattr(row, name, value)
        await self._flush_checking_company()
        await self._session.refresh(row)  # company_name follows a changed company_id
        return row

    async def delete(self, row: ApplicationRow) -> None:
        # Its transitions go with it: the foreign key cascades on delete.
        await self._session.delete(row)
        await self._session.flush()

    async def undo_latest_transition(self, application: Application) -> None:
        latest = await self._session.scalar(
            select(TransitionRow)
            .where(TransitionRow.application_id == application.id)
            .order_by(TransitionRow.occurred_on.desc(), TransitionRow.id.desc())
            .limit(1)
        )
        if latest is not None:
            await self._session.delete(latest)
        row = await self._session.get_one(ApplicationRow, application.id)
        row.stage = application.stage
        row.outcome = application.outcome

    async def list_page(
        self, filters: ApplicationFilters, page: PageParams
    ) -> tuple[list[ApplicationRow], int]:
        conditions = _conditions(filters)
        rows = await self._session.scalars(
            select(ApplicationRow)
            .where(*conditions)
            .order_by(ApplicationRow.created_at.desc(), ApplicationRow.id.desc())
            .limit(page.limit)
            .offset(page.offset)
        )
        total = await self._session.scalar(
            select(func.count()).select_from(ApplicationRow).where(*conditions)
        )
        return list(rows), total or 0

    async def save_transition(self, application: Application, transition: Transition) -> None:
        row = await self._session.get_one(ApplicationRow, application.id)
        row.stage = application.stage
        row.outcome = application.outcome
        self._session.add(_transition_row(application.id, transition))

    async def list_transitions(self, application_id: UUID) -> list[Transition]:
        rows = await self._session.scalars(
            select(TransitionRow)
            .where(TransitionRow.application_id == application_id)
            .order_by(TransitionRow.occurred_on, TransitionRow.id)
        )
        return [
            Transition(
                from_stage=row.from_stage,
                to_stage=row.to_stage,
                outcome=row.outcome,
                occurred_on=row.occurred_on,
                note=row.note,
            )
            for row in rows
        ]

    async def _flush_checking_company(self) -> None:
        try:
            # Flush now so a missing company surfaces here as a request error, not at commit.
            await self._session.flush()
        except IntegrityError as error:
            if COMPANY_FOREIGN_KEY in str(error.orig):
                raise UnknownCompanyError("The company does not exist") from error
            raise


def _conditions(filters: ApplicationFilters) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if filters.stage is not None:
        conditions.append(ApplicationRow.stage == filters.stage)
    if filters.outcome is not None:
        conditions.append(ApplicationRow.outcome == filters.outcome)
    if filters.channel is not None:
        conditions.append(ApplicationRow.channel == filters.channel)
    if filters.active is not None:
        is_open = ApplicationRow.outcome.is_(None)
        conditions.append(is_open if filters.active else ~is_open)
    return conditions


def _transition_row(application_id: UUID, transition: Transition) -> TransitionRow:
    return TransitionRow(
        application_id=application_id,
        from_stage=transition.from_stage,
        to_stage=transition.to_stage,
        outcome=transition.outcome,
        occurred_on=transition.occurred_on,
        note=transition.note,
    )
