from collections.abc import Mapping
from uuid import UUID

from funnel.core.exceptions import NotFoundError
from funnel.core.pagination import PageParams
from funnel.modules.discovery.models import SearchProfileRow
from funnel.modules.discovery.repository import SearchProfileRepository
from funnel.modules.discovery.schemas import SearchProfileCreate


class SearchProfileService:
    """Profiles have no rules beyond validation: plain CRUD on rows."""

    def __init__(self, repository: SearchProfileRepository) -> None:
        self._repository = repository

    async def create(self, profile: SearchProfileCreate) -> SearchProfileRow:
        return await self._repository.add(SearchProfileRow(**profile.model_dump()))

    async def get(self, profile_id: UUID) -> SearchProfileRow:
        profile = await self._repository.get(profile_id)
        if profile is None:
            raise NotFoundError(f"Search profile {profile_id} does not exist")
        return profile

    async def update(self, profile_id: UUID, changes: Mapping[str, object]) -> SearchProfileRow:
        profile = await self.get(profile_id)
        return await self._repository.update(profile, changes)

    async def delete(self, profile_id: UUID) -> None:
        profile = await self.get(profile_id)
        await self._repository.delete(profile)

    async def list_page(self, page: PageParams) -> tuple[list[SearchProfileRow], int]:
        return await self._repository.list_page(page)
