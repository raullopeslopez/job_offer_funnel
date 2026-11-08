from http import HTTPStatus
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from funnel.core.db import get_session
from funnel.core.errors import ProblemRead
from funnel.core.pagination import Page, PageParams, get_page_params
from funnel.modules.discovery.repository import SearchProfileRepository
from funnel.modules.discovery.schemas import (
    SearchProfileCreate,
    SearchProfileRead,
    SearchProfileUpdate,
)
from funnel.modules.discovery.service import SearchProfileService

router = APIRouter(prefix="/search-profiles", tags=["discovery"])


def get_search_profile_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SearchProfileService:
    # Composition root: the only place in the router that knows about the repository.
    return SearchProfileService(SearchProfileRepository(session))


Service = Annotated[SearchProfileService, Depends(get_search_profile_service)]

_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    HTTPStatus.NOT_FOUND: {"model": ProblemRead, "description": "Search profile does not exist"}
}
_NAME_TAKEN: dict[int | str, dict[str, Any]] = {
    HTTPStatus.CONFLICT: {
        "model": ProblemRead,
        "description": "A search profile with that name already exists (`already-exists`)",
    }
}


@router.post("", status_code=HTTPStatus.CREATED, responses=_NAME_TAKEN)
async def create_search_profile(
    profile: SearchProfileCreate, service: Service
) -> SearchProfileRead:
    """Describe what you look for. Lists are trimmed and repeated words kept once."""
    created = await service.create(profile)
    return SearchProfileRead.model_validate(created, from_attributes=True)


@router.get("")
async def list_search_profiles(
    page: Annotated[PageParams, Depends(get_page_params)], service: Service
) -> Page[SearchProfileRead]:
    """Search profiles in alphabetical order, ignoring case."""
    profiles, total = await service.list_page(page)
    return Page(
        items=[SearchProfileRead.model_validate(row, from_attributes=True) for row in profiles],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{profile_id}", responses=_NOT_FOUND)
async def read_search_profile(profile_id: UUID, service: Service) -> SearchProfileRead:
    profile = await service.get(profile_id)
    return SearchProfileRead.model_validate(profile, from_attributes=True)


@router.patch("/{profile_id}", responses={**_NOT_FOUND, **_NAME_TAKEN})
async def update_search_profile(
    profile_id: UUID, changes: SearchProfileUpdate, service: Service
) -> SearchProfileRead:
    """Change only the fields sent."""
    updated = await service.update(profile_id, changes.model_dump(exclude_unset=True))
    return SearchProfileRead.model_validate(updated, from_attributes=True)


@router.delete("/{profile_id}", status_code=HTTPStatus.NO_CONTENT, responses=_NOT_FOUND)
async def delete_search_profile(profile_id: UUID, service: Service) -> None:
    await service.delete(profile_id)
