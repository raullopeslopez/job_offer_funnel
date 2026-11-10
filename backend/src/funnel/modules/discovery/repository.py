from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from funnel.core.db import flush_checking_references, flush_checking_unique
from funnel.core.pagination import PageParams
from funnel.modules.discovery.domain import FeedTakenError, ImportMethod
from funnel.modules.discovery.models import (
    UNIQUE_JOB_BOARD_FEED,
    UNIQUE_JOB_BOARD_NAME_INDEX,
    UNIQUE_PROFILE_NAME_INDEX,
    JobBoardRow,
    SearchProfileRow,
)


class SearchProfileRepository:
    """Never commits: the request session does."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, profile: SearchProfileRow) -> SearchProfileRow:
        self._session.add(profile)
        await self._flush_checking_name(profile)
        return profile

    async def get(self, profile_id: UUID) -> SearchProfileRow | None:
        return await self._session.get(SearchProfileRow, profile_id)

    async def update(
        self, profile: SearchProfileRow, changes: Mapping[str, object]
    ) -> SearchProfileRow:
        for name, value in changes.items():
            setattr(profile, name, value)
        await self._flush_checking_name(profile)
        return profile

    async def delete(self, profile: SearchProfileRow) -> None:
        await self._session.delete(profile)
        await self._session.flush()

    async def list_page(self, page: PageParams) -> tuple[list[SearchProfileRow], int]:
        rows = await self._session.scalars(
            select(SearchProfileRow)
            .order_by(func.lower(SearchProfileRow.name), SearchProfileRow.id)
            .limit(page.limit)
            .offset(page.offset)
        )
        total = await self._session.scalar(select(func.count()).select_from(SearchProfileRow))
        return list(rows), total or 0

    async def list_all(self) -> list[SearchProfileRow]:
        """Every profile: there are a handful, so no pagination."""
        rows = await self._session.scalars(
            select(SearchProfileRow).order_by(SearchProfileRow.created_at, SearchProfileRow.id)
        )
        return list(rows)

    async def _flush_checking_name(self, profile: SearchProfileRow) -> None:
        detail = f"A search profile named {profile.name} already exists"
        await flush_checking_unique(self._session, UNIQUE_PROFILE_NAME_INDEX, detail)


class JobBoardRepository:
    """Never commits: the request session does."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, job_board: JobBoardRow) -> JobBoardRow:
        self._session.add(job_board)
        await self._flush_checking_name(job_board)
        return job_board

    async def get(self, job_board_id: UUID) -> JobBoardRow | None:
        return await self._session.get(JobBoardRow, job_board_id)

    async def update(self, job_board: JobBoardRow, changes: Mapping[str, object]) -> JobBoardRow:
        for name, value in changes.items():
            setattr(job_board, name, value)
        await self._flush_checking_name(job_board)
        return job_board

    async def record_import(self, job_board: JobBoardRow, imported_at: datetime) -> None:
        job_board.last_imported_at = imported_at
        await self._session.flush()

    async def delete(self, job_board: JobBoardRow) -> None:
        # Offers in the inbox reference job boards with ON DELETE RESTRICT.
        detail = f"Job board {job_board.id} still has offers"
        await self._session.delete(job_board)
        await flush_checking_references(self._session, detail)

    async def list_page(self, page: PageParams) -> tuple[list[JobBoardRow], int]:
        rows = await self._session.scalars(
            select(JobBoardRow)
            .order_by(func.lower(JobBoardRow.name), JobBoardRow.id)
            .limit(page.limit)
            .offset(page.offset)
        )
        total = await self._session.scalar(select(func.count()).select_from(JobBoardRow))
        return list(rows), total or 0

    async def list_searched_by_hand(self) -> list[JobBoardRow]:
        """Every job board that is not imported, alphabetically: there are a handful, so
        no pagination."""
        rows = await self._session.scalars(
            select(JobBoardRow)
            .where(JobBoardRow.import_method == ImportMethod.NONE)
            .order_by(func.lower(JobBoardRow.name), JobBoardRow.id)
        )
        return list(rows)

    async def _flush_checking_name(self, job_board: JobBoardRow) -> None:
        detail = f"A job board named {job_board.name} already exists"
        feed_taken = f"Another job board already imports the feed {job_board.feed}"
        try:
            await flush_checking_unique(self._session, UNIQUE_JOB_BOARD_NAME_INDEX, detail)
        except IntegrityError as error:
            if UNIQUE_JOB_BOARD_FEED in str(error.orig):
                raise FeedTakenError(feed_taken) from error
            raise
