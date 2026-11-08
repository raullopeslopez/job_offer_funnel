from http import HTTPStatus
from typing import Any
from uuid import UUID

from fastapi import APIRouter

from funnel.core.errors import ProblemRead, ValidationProblemRead
from funnel.modules.applications.schemas import ApplicationRead, TransitionCreate, TransitionRead

router = APIRouter(prefix="/applications", tags=["applications"])

_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    HTTPStatus.NOT_FOUND: {"model": ProblemRead, "description": "Application does not exist"}
}


@router.get("/{application_id}", responses=_NOT_FOUND)
async def read_application(application_id: UUID) -> ApplicationRead:
    raise NotImplementedError


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
async def create_transition(application_id: UUID, transition: TransitionCreate) -> TransitionRead:
    """Move the application to a later stage, or close it with an outcome."""
    raise NotImplementedError


@router.get("/{application_id}/transitions", responses=_NOT_FOUND)
async def list_transitions(application_id: UUID) -> list[TransitionRead]:
    """Transition history, oldest first."""
    raise NotImplementedError
