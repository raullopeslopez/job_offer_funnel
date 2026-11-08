from uuid import UUID

from funnel.core.clock import Clock
from funnel.core.exceptions import NotFoundError
from funnel.modules.applications.domain import Application, StageChange, Transition
from funnel.modules.applications.repository import ApplicationRepository


class ApplicationService:
    def __init__(self, repository: ApplicationRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    async def get(self, application_id: UUID) -> Application:
        application = await self._repository.get(application_id)
        if application is None:
            raise NotFoundError(f"Application {application_id} does not exist")
        return application

    async def record_transition(self, application_id: UUID, change: StageChange) -> Transition:
        application = await self.get(application_id)
        transition = application.apply(change, self._clock.today())
        await self._repository.save_transition(application, transition)
        return transition

    async def list_transitions(self, application_id: UUID) -> list[Transition]:
        await self.get(application_id)
        return await self._repository.list_transitions(application_id)
