from http import HTTPStatus
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from funnel.core.clock import Clock, get_clock
from funnel.core.db import SessionDep
from funnel.core.errors import ProblemRead, ValidationProblemRead
from funnel.core.pagination import Page, PageParams, get_page_params
from funnel.modules.applications.domain import StageChange
from funnel.modules.applications.repository import ApplicationRepository
from funnel.modules.applications.schemas import (
    ApplicationCreate,
    ApplicationDetailRead,
    ApplicationFilters,
    ApplicationRead,
    ApplicationUpdate,
    TransitionCreate,
    TransitionRead,
)
from funnel.modules.applications.service import ApplicationService

router = APIRouter(prefix="/applications", tags=["applications"])


def get_application_service(
    session: SessionDep,
    clock: Annotated[Clock, Depends(get_clock)],
) -> ApplicationService:
    # Composition root: the only place in the router that knows about the repository.
    return ApplicationService(ApplicationRepository(session), clock)


Service = Annotated[ApplicationService, Depends(get_application_service)]

_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    HTTPStatus.NOT_FOUND: {"model": ProblemRead, "description": "Application does not exist"}
}


_INVALID_DATA: dict[int | str, dict[str, Any]] = {
    HTTPStatus.UNPROCESSABLE_CONTENT: {
        "model": ValidationProblemRead | ProblemRead,
        "description": "Invalid body (`validation-error`), or the company does not exist "
        "(`unknown-company`)",
    }
}


@router.post(
    "",
    status_code=HTTPStatus.CREATED,
    responses={
        HTTPStatus.UNPROCESSABLE_CONTENT: {
            "model": ValidationProblemRead | ProblemRead,
            "description": "Invalid body (`validation-error`), the company does not exist "
            "(`unknown-company`), or the date is in the future (`invalid-transition-date`)",
        }
    },
)
async def create_application(application: ApplicationCreate, service: Service) -> ApplicationRead:
    """Create an application in `evaluated` (default) or `applied`; that is its first transition."""
    created = await service.create(application)
    return ApplicationRead.model_validate(created, from_attributes=True)


@router.get("")
async def list_applications(
    filters: Annotated[ApplicationFilters, Query()],
    page: Annotated[PageParams, Depends(get_page_params)],
    service: Service,
) -> Page[ApplicationRead]:
    """Applications from the most recently created. Filters combine with AND."""
    applications, total = await service.list_page(filters, page)
    return Page(
        items=[ApplicationRead.model_validate(row, from_attributes=True) for row in applications],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{application_id}", responses=_NOT_FOUND)
async def read_application(application_id: UUID, service: Service) -> ApplicationDetailRead:
    """The application with its transition history."""
    application = await service.get_row(application_id)
    transitions = await service.list_transitions(application_id)
    return ApplicationDetailRead(
        **ApplicationRead.model_validate(application, from_attributes=True).model_dump(),
        transitions=[
            TransitionRead.model_validate(item, from_attributes=True) for item in transitions
        ],
    )


@router.patch("/{application_id}", responses={**_NOT_FOUND, **_INVALID_DATA})
async def update_application(
    application_id: UUID, changes: ApplicationUpdate, service: Service
) -> ApplicationRead:
    """Change only the fields sent. The stage changes only through transitions."""
    updated = await service.update(application_id, changes.model_dump(exclude_unset=True))
    return ApplicationRead.model_validate(updated, from_attributes=True)


@router.delete("/{application_id}", status_code=HTTPStatus.NO_CONTENT, responses=_NOT_FOUND)
async def delete_application(application_id: UUID, service: Service) -> None:
    """Delete an application created by mistake, with its history.

    To archive one instead, close it with an outcome: it still counts in the metrics.
    """
    await service.delete(application_id)


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


@router.delete(
    "/{application_id}/transitions/latest",
    status_code=HTTPStatus.NO_CONTENT,
    responses={
        **_NOT_FOUND,
        HTTPStatus.CONFLICT: {
            "model": ProblemRead,
            "description": "Only the first stage is left, which cannot be undone "
            "(`invalid-transition`)",
        },
    },
)
async def undo_latest_transition(application_id: UUID, service: Service) -> None:
    """Undo the most recent transition: the application returns to its previous state."""
    await service.undo_latest_transition(application_id)
