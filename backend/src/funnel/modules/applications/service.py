from collections.abc import Mapping
from uuid import UUID

from funnel.core.clock import Clock
from funnel.core.exceptions import NotFoundError
from funnel.core.pagination import PageParams
from funnel.modules.applications.domain import (
    Application,
    StageChange,
    Transition,
    first_transition,
)
from funnel.modules.applications.models import ApplicationRow
from funnel.modules.applications.repository import ApplicationRepository
from funnel.modules.applications.schemas import ApplicationCreate, ApplicationFilters


class ApplicationService:
    """Stage changes go through the domain; the descriptive fields are plain CRUD on rows."""

    def __init__(self, repository: ApplicationRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    async def create(self, application: ApplicationCreate) -> ApplicationRow:
        first = first_transition(application.stage, application.occurred_on, self._clock.today())
        row = ApplicationRow(
            **application.model_dump(exclude={"stage", "occurred_on"}), stage=first.to_stage
        )
        return await self._repository.add(row, first)

    async def get(self, application_id: UUID) -> Application:
        application = await self._repository.get(application_id)
        if application is None:
            raise _not_found(application_id)
        return application

    async def get_row(self, application_id: UUID) -> ApplicationRow:
        row = await self._repository.get_row(application_id)
        if row is None:
            raise _not_found(application_id)
        return row

    async def update(self, application_id: UUID, changes: Mapping[str, object]) -> ApplicationRow:
        row = await self.get_row(application_id)
        return await self._repository.update(row, changes)

    async def delete(self, application_id: UUID) -> None:
        row = await self.get_row(application_id)
        await self._repository.delete(row)

    async def undo_latest_transition(self, application_id: UUID) -> None:
        application = await self.get(application_id)
        history = await self._repository.list_transitions(application_id)
        application.undo_latest(history)
        await self._repository.undo_latest_transition(application)

    async def list_page(
        self, filters: ApplicationFilters, page: PageParams
    ) -> tuple[list[ApplicationRow], int]:
        return await self._repository.list_page(filters, page)

    async def record_transition(self, application_id: UUID, change: StageChange) -> Transition:
        application = await self.get(application_id)
        transition = application.apply(change, self._clock.today())
        await self._repository.save_transition(application, transition)
        return transition

    async def list_transitions(self, application_id: UUID) -> list[Transition]:
        await self.get(application_id)
        return await self._repository.list_transitions(application_id)


def _not_found(application_id: UUID) -> NotFoundError:
    return NotFoundError(f"Application {application_id} does not exist")
