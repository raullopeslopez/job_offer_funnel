from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from funnel.core.exceptions import AlreadyExistsError
from funnel.core.pagination import PageParams
from funnel.modules.inbox.domain import OfferStatus, UnknownJobBoardError
from funnel.modules.inbox.models import JOB_BOARD_FOREIGN_KEY, UNIQUE_DUPLICATE_KEY, OfferRow


class OfferRepository:
    """Never commits: the request session does."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, offer: OfferRow) -> OfferRow:
        # Read before flushing: after a failed flush the row cannot be loaded any more.
        duplicate = f"An offer for {offer.company} as {offer.title} already exists"
        self._session.add(offer)
        try:
            await self._session.flush()
        except IntegrityError as error:
            if UNIQUE_DUPLICATE_KEY in str(error.orig):
                raise AlreadyExistsError(duplicate) from error
            if JOB_BOARD_FOREIGN_KEY in str(error.orig):
                raise UnknownJobBoardError("The job board does not exist") from error
            raise
        await self._session.refresh(offer)  # loads created_at and job_board_name
        return offer

    async def get(self, offer_id: UUID) -> OfferRow | None:
        return await self._session.get(OfferRow, offer_id)

    async def save(self, offer: OfferRow) -> OfferRow:
        await self._session.flush()
        # The flush expires job_board_name; reload it here, not lazily outside async code.
        await self._session.refresh(offer)
        return offer

    async def list_page(
        self, status: OfferStatus | None, page: PageParams
    ) -> tuple[list[OfferRow], int]:
        conditions = [] if status is None else [OfferRow.status == status]
        rows = await self._session.scalars(
            select(OfferRow)
            .where(*conditions)
            .order_by(OfferRow.created_at.desc(), OfferRow.id.desc())
            .limit(page.limit)
            .offset(page.offset)
        )
        total = await self._session.scalar(
            select(func.count()).select_from(OfferRow).where(*conditions)
        )
        return list(rows), total or 0
