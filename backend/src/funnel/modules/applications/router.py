from http import HTTPStatus
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from funnel.core.clock import Clock, get_clock
from funnel.core.db import get_session
from funnel.core.errors import ProblemRead, ValidationProblemRead
from funnel.modules.applications.domain import StageChange
from funnel.modules.applications.repository import ApplicationRepository
from funnel.modules.applications.schemas import ApplicationRead, TransitionCreate, TransitionRead
from funnel.modules.applications.service import ApplicationService

router = APIRouter(prefix="/applications", tags=["applications"])


def get_application_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> ApplicationService:
    # Composition root: the only place in the router that knows about the repository.
    return ApplicationService(ApplicationRepository(session), clock)


Service = Annotated[ApplicationService, Depends(get_application_service)]

_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    HTTPStatus.NOT_FOUND: {"model": ProblemRead, "description": "Application does not exist"}
}


@router.get("/{application_id}", responses=_NOT_FOUND)
async def read_application(application_id: UUID, service: Service) -> ApplicationRead:
    application = await service.get(application_id)
    return ApplicationRead.model_validate(application, from_attributes=True)


@router.post(
    "/{application_id}/transitions",
    status_code=HTTPStatus.CREATED,
    responses={
        **_NOT_FOUND,
        HTTPStatus.CONFLICT: {
            "model": ProblemRead,
            "description": "Transition not allowed from the current state (`invalid-transition`)",
        },
        HTTPStatus.UNPROCESSABLE_CONTENT: {
            "model": ValidationProblemRead | ProblemRead,
            "description": "Invalid body (`validation-error`), or date in the future or "
            "before the previous transition (`invalid-transition-date`)",
        },
    },
)
async def create_transition(
    application_id: UUID, transition: TransitionCreate, service: Service
) -> TransitionRead:
    """Move the application to a later stage, or close it with an outcome."""
    change = StageChange(**transition.model_dump())
    recorded = await service.record_transition(application_id, change)
    return TransitionRead.model_validate(recorded, from_attributes=True)


@router.get("/{application_id}/transitions", responses=_NOT_FOUND)
async def list_transitions(application_id: UUID, service: Service) -> list[TransitionRead]:
    """Transition history, oldest first."""
    transitions = await service.list_transitions(application_id)
    return [TransitionRead.model_validate(item, from_attributes=True) for item in transitions]
