from http import HTTPStatus
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends

from funnel.core.db import SessionDep
from funnel.core.errors import ProblemRead
from funnel.core.pagination import Page, PageParams, get_page_params
from funnel.modules.discovery.domain import WorkMode
from funnel.modules.discovery.repository import JobBoardRepository, SearchProfileRepository
from funnel.modules.discovery.schemas import (
    GeneratedSearchRead,
    JobBoardCreate,
    JobBoardRead,
    JobBoardSearchesRead,
    JobBoardUpdate,
    ProfileSearchesRead,
    SearchProfileCreate,
    SearchProfileRead,
    SearchProfileUpdate,
)
from funnel.modules.discovery.service import (
    JobBoardService,
    SearchGenerationService,
    SearchProfileService,
)

profiles_router = APIRouter(prefix="/search-profiles", tags=["discovery"])


def get_search_profile_service(
    session: SessionDep,
) -> SearchProfileService:
    # Composition root: the only place in the router that knows about the repository.
    return SearchProfileService(SearchProfileRepository(session))


ProfileServiceDependency = Annotated[SearchProfileService, Depends(get_search_profile_service)]

_PROFILE_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    HTTPStatus.NOT_FOUND: {"model": ProblemRead, "description": "Search profile does not exist"}
}
_PROFILE_NAME_TAKEN: dict[int | str, dict[str, Any]] = {
    HTTPStatus.CONFLICT: {
        "model": ProblemRead,
        "description": "A search profile with that name already exists (`already-exists`)",
    }
}


@profiles_router.post("", status_code=HTTPStatus.CREATED, responses=_PROFILE_NAME_TAKEN)
async def create_search_profile(
    profile: SearchProfileCreate, service: ProfileServiceDependency
) -> SearchProfileRead:
    """Describe what you look for. Lists are trimmed and repeated words kept once."""
    created = await service.create(profile)
    return SearchProfileRead.model_validate(created, from_attributes=True)


@profiles_router.get("")
async def list_search_profiles(
    page: Annotated[PageParams, Depends(get_page_params)], service: ProfileServiceDependency
) -> Page[SearchProfileRead]:
    """Search profiles in alphabetical order, ignoring case."""
    profiles, total = await service.list_page(page)
    return Page(
        items=[SearchProfileRead.model_validate(row, from_attributes=True) for row in profiles],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@profiles_router.get("/{profile_id}", responses=_PROFILE_NOT_FOUND)
async def read_search_profile(
    profile_id: UUID, service: ProfileServiceDependency
) -> SearchProfileRead:
    profile = await service.get(profile_id)
    return SearchProfileRead.model_validate(profile, from_attributes=True)


@profiles_router.patch("/{profile_id}", responses={**_PROFILE_NOT_FOUND, **_PROFILE_NAME_TAKEN})
async def update_search_profile(
    profile_id: UUID, changes: SearchProfileUpdate, service: ProfileServiceDependency
) -> SearchProfileRead:
    """Change only the fields sent."""
    updated = await service.update(profile_id, changes.model_dump(exclude_unset=True))
    return SearchProfileRead.model_validate(updated, from_attributes=True)


@profiles_router.delete(
    "/{profile_id}", status_code=HTTPStatus.NO_CONTENT, responses=_PROFILE_NOT_FOUND
)
async def delete_search_profile(profile_id: UUID, service: ProfileServiceDependency) -> None:
    await service.delete(profile_id)


def get_search_generation_service(
    session: SessionDep,
) -> SearchGenerationService:
    return SearchGenerationService(SearchProfileRepository(session), JobBoardRepository(session))


@profiles_router.get("/{profile_id}/searches", responses=_PROFILE_NOT_FOUND)
async def generate_searches(
    profile_id: UUID,
    service: Annotated[SearchGenerationService, Depends(get_search_generation_service)],
) -> ProfileSearchesRead:
    """The profile's search for every job board, in its syntax, with a URL ready to open.

    Computed on every request: editing the profile or a job board updates the searches.
    """
    profile, job_boards = await service.generate(profile_id)
    return ProfileSearchesRead(
        profile_id=profile.id,
        work_modes=[WorkMode(mode) for mode in profile.work_modes],
        job_boards=[
            JobBoardSearchesRead(
                job_board_id=job_board.id,
                job_board_name=job_board.name,
                syntax=job_board.syntax,
                searches=[
                    GeneratedSearchRead(query=search.query, url=search.url) for search in searches
                ],
            )
            for job_board, searches in job_boards
        ],
    )


# --- Job boards ---

job_boards_router = APIRouter(prefix="/job-boards", tags=["discovery"])


def get_job_board_service(
    session: SessionDep,
) -> JobBoardService:
    return JobBoardService(JobBoardRepository(session))


JobBoardServiceDependency = Annotated[JobBoardService, Depends(get_job_board_service)]

_JOB_BOARD_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    HTTPStatus.NOT_FOUND: {"model": ProblemRead, "description": "Job board does not exist"}
}
_JOB_BOARD_NAME_TAKEN: dict[int | str, dict[str, Any]] = {
    HTTPStatus.CONFLICT: {
        "model": ProblemRead,
        "description": "A job board with that name already exists (`already-exists`)",
    }
}


@job_boards_router.post("", status_code=HTTPStatus.CREATED, responses=_JOB_BOARD_NAME_TAKEN)
async def create_job_board(
    job_board: JobBoardCreate, service: JobBoardServiceDependency
) -> JobBoardRead:
    """Register a job board with its search URL template and search syntax."""
    created = await service.create(job_board)
    return JobBoardRead.model_validate(created, from_attributes=True)


@job_boards_router.get("")
async def list_job_boards(
    page: Annotated[PageParams, Depends(get_page_params)], service: JobBoardServiceDependency
) -> Page[JobBoardRead]:
    """Job boards in alphabetical order, ignoring case."""
    job_boards, total = await service.list_page(page)
    return Page(
        items=[JobBoardRead.model_validate(row, from_attributes=True) for row in job_boards],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@job_boards_router.get("/{job_board_id}", responses=_JOB_BOARD_NOT_FOUND)
async def read_job_board(job_board_id: UUID, service: JobBoardServiceDependency) -> JobBoardRead:
    job_board = await service.get(job_board_id)
    return JobBoardRead.model_validate(job_board, from_attributes=True)


@job_boards_router.patch(
    "/{job_board_id}", responses={**_JOB_BOARD_NOT_FOUND, **_JOB_BOARD_NAME_TAKEN}
)
async def update_job_board(
    job_board_id: UUID, changes: JobBoardUpdate, service: JobBoardServiceDependency
) -> JobBoardRead:
    """Change only the fields sent."""
    updated = await service.update(job_board_id, changes.model_dump(exclude_unset=True))
    return JobBoardRead.model_validate(updated, from_attributes=True)


@job_boards_router.delete(
    "/{job_board_id}",
    status_code=HTTPStatus.NO_CONTENT,
    responses={
        **_JOB_BOARD_NOT_FOUND,
        HTTPStatus.CONFLICT: {
            "model": ProblemRead,
            "description": "Offers in the inbox come from this job board (`in-use`)",
        },
    },
)
async def delete_job_board(job_board_id: UUID, service: JobBoardServiceDependency) -> None:
    await service.delete(job_board_id)


router = APIRouter()
router.include_router(profiles_router)
router.include_router(job_boards_router)
