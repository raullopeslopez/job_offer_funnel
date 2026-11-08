from collections.abc import Mapping
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from funnel.core.exceptions import AlreadyExistsError
from funnel.core.pagination import PageParams
from funnel.modules.discovery.models import UNIQUE_PROFILE_NAME_INDEX, SearchProfileRow


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

    async def _flush_checking_name(self, profile: SearchProfileRow) -> None:
        # Read before flushing: after a failed flush the row cannot be loaded any more.
        detail = f"A search profile named {profile.name} already exists"
        try:
            # Flush now so a duplicate name surfaces here as a business error, not at commit.
            await self._session.flush()
        except IntegrityError as error:
            if UNIQUE_PROFILE_NAME_INDEX in str(error.orig):
                raise AlreadyExistsError(detail) from error
            raise
