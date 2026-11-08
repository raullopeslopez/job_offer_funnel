from collections.abc import Collection, Sequence
from datetime import datetime
from typing import Any, cast
from uuid import UUID, uuid7

from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from funnel.core.exceptions import AlreadyExistsError
from funnel.core.pagination import PageParams
from funnel.modules.inbox.domain import EXPIRED_REASON, Feed, OfferStatus, UnknownJobBoardError
from funnel.modules.inbox.models import (
    JOB_BOARD_FOREIGN_KEY,
    UNIQUE_DUPLICATE_KEY,
    FeedImportRow,
    OfferRow,
)


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


class FeedImportRepository:
    """Offers coming from feeds, and when each feed was last imported.

    Never commits: the request session does.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_new(self, offers: Sequence[OfferRow]) -> int:
        """Insert the offers that are not duplicates; return how many were inserted.

        ON CONFLICT DO NOTHING keeps the UNIQUE constraint as the judge of duplicates
        without aborting the transaction, as a failed flush would.
        """
        if not offers:
            return 0
        values = [
            {
                column.key: getattr(offer, column.key)
                for column in OfferRow.__table__.columns
                if getattr(offer, column.key) is not None
            }
            | {"id": offer.id or uuid7()}
            for offer in offers
        ]
        inserted = await self._session.scalars(
            insert(OfferRow)
            .values(values)
            .on_conflict_do_nothing(constraint=UNIQUE_DUPLICATE_KEY)
            .returning(OfferRow.id)
        )
        return len(inserted.all())

    async def expire_missing(self, feed: Feed, published_urls: Collection[str]) -> int:
        """Discard as expired the pending offers of `feed` that it no longer publishes."""
        result = await self._session.execute(
            update(OfferRow)
            .where(
                OfferRow.feed == feed,
                OfferRow.status == OfferStatus.PENDING,
                OfferRow.url.not_in(published_urls),
            )
            .values(status=OfferStatus.DISCARDED, discard_reason=EXPIRED_REASON)
        )
        return cast(CursorResult[Any], result).rowcount

    async def last_imports(self) -> dict[Feed, datetime]:
        rows = await self._session.scalars(select(FeedImportRow))
        return {row.feed: row.last_imported_at for row in rows}

    async def record(self, feed: Feed, imported_at: datetime) -> None:
        await self._session.execute(
            insert(FeedImportRow)
            .values(feed=feed, last_imported_at=imported_at)
            .on_conflict_do_update(
                index_elements=[FeedImportRow.feed], set_={"last_imported_at": imported_at}
            )
        )
