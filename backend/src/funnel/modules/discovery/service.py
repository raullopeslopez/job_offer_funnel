from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from funnel.core.exceptions import NotFoundError
from funnel.core.pagination import PageParams
from funnel.modules.discovery.domain import (
    EmailAlert,
    GeneratedSearch,
    SearchTerms,
    build_queries,
    build_url,
)
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

    async def all_terms(self) -> list[SearchTerms]:
        """What every profile looks for, from the oldest: imports filter offers with them."""
        return [
            SearchTerms(row.titles, row.keywords, row.excluded_keywords)
            for row in await self._repository.list_all()
        ]


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

    async def find_by_email_alert(self, email_alert: EmailAlert) -> JobBoardRow | None:
        """The job board that imports the email alert, if any."""
        return await self._repository.get_by_email_alert(email_alert)

    async def record_import(self, job_board: JobBoardRow, imported_at: datetime) -> None:
        await self._repository.record_import(job_board, imported_at)


class SearchGenerationService:
    """Builds a profile's searches for every job board that is not imported; nothing is
    stored."""

    def __init__(self, profiles: SearchProfileRepository, job_boards: JobBoardRepository) -> None:
        self._profiles = profiles
        self._job_boards = job_boards

    async def generate(
        self, profile_id: UUID
    ) -> tuple[SearchProfileRow, list[tuple[JobBoardRow, list[GeneratedSearch]]]]:
        profile = await self._profiles.get(profile_id)
        if profile is None:
            raise NotFoundError(f"Search profile {profile_id} does not exist")
        terms = SearchTerms(
            titles=profile.titles,
            keywords=profile.keywords,
            excluded_keywords=profile.excluded_keywords,
        )
        job_boards = await self._job_boards.list_searched_by_hand()
        return profile, [
            (job_board, _searches(job_board, terms, profile.location)) for job_board in job_boards
        ]


def _searches(
    job_board: JobBoardRow, terms: SearchTerms, location: str | None
) -> list[GeneratedSearch]:
    return [
        GeneratedSearch(query, build_url(job_board.search_url_template, query, location))
        for query in build_queries(terms, job_board.syntax)
    ]


def build_search_profile_service(session: AsyncSession) -> SearchProfileService:
    """For other modules: the service on their request session, without its repository."""
    return SearchProfileService(SearchProfileRepository(session))


def build_job_board_service(session: AsyncSession) -> JobBoardService:
    """For other modules: the service on their request session, without its repository."""
    return JobBoardService(JobBoardRepository(session))
