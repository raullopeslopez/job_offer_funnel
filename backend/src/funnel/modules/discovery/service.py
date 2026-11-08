from collections.abc import Mapping
from uuid import UUID

from funnel.core.exceptions import NotFoundError
from funnel.core.pagination import PageParams
from funnel.modules.discovery.models import JobBoardRow, SearchProfileRow
from funnel.modules.discovery.repository import JobBoardRepository, SearchProfileRepository
from funnel.modules.discovery.schemas import JobBoardCreate, SearchProfileCreate


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


class JobBoardService:
    """Job boards have no rules beyond validation: plain CRUD on rows."""

    def __init__(self, repository: JobBoardRepository) -> None:
        self._repository = repository

    async def create(self, job_board: JobBoardCreate) -> JobBoardRow:
        return await self._repository.add(JobBoardRow(**job_board.model_dump()))

    async def get(self, job_board_id: UUID) -> JobBoardRow:
        job_board = await self._repository.get(job_board_id)
        if job_board is None:
            raise NotFoundError(f"Job board {job_board_id} does not exist")
        return job_board

    async def update(self, job_board_id: UUID, changes: Mapping[str, object]) -> JobBoardRow:
        job_board = await self.get(job_board_id)
        return await self._repository.update(job_board, changes)

    async def delete(self, job_board_id: UUID) -> None:
        job_board = await self.get(job_board_id)
        await self._repository.delete(job_board)

    async def list_page(self, page: PageParams) -> tuple[list[JobBoardRow], int]:
        return await self._repository.list_page(page)
