from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from funnel.modules.applications.domain import Application, Transition
from funnel.modules.applications.models import ApplicationRow, TransitionRow


class ApplicationRepository:
    """Maps ORM rows to domain objects. Never commits: the request session does."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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

    async def save_transition(self, application: Application, transition: Transition) -> None:
        row = await self._session.get_one(ApplicationRow, application.id)
        row.stage = application.stage
        row.outcome = application.outcome
        self._session.add(
            TransitionRow(
                application_id=application.id,
                from_stage=transition.from_stage,
                to_stage=transition.to_stage,
                outcome=transition.outcome,
                occurred_on=transition.occurred_on,
                note=transition.note,
            )
        )

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
