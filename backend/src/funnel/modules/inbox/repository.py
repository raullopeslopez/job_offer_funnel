from collections.abc import Collection, Sequence
from typing import Any, cast
from uuid import UUID, uuid7

from sqlalchemy import (
    ColumnElement,
    CursorResult,
    Select,
    and_,
    exists,
    false,
    func,
    not_,
    or_,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import with_expression

from funnel.core.db import flush_checking_unique
from funnel.core.exceptions import AlreadyExistsError
from funnel.core.pagination import PageParams
from funnel.modules.discovery.domain import SearchTerms
from funnel.modules.inbox.domain import (
    EXPIRED_REASON,
    OfferStatus,
    Reading,
    UnknownJobBoardError,
)
from funnel.modules.inbox.models import (
    JOB_BOARD_FOREIGN_KEY,
    UNIQUE_DUPLICATE_KEY,
    UNIQUE_WATCHED_NAME_INDEX,
    OfferReadingRow,
    OfferRow,
    WatchedCompanyRow,
)


def _read_for(location: str | None) -> ColumnElement[bool]:
    return and_(
        OfferReadingRow.offer_id == OfferRow.id,
        OfferReadingRow.location.is_not_distinct_from(location),
    )


def _contradicted(terms: SearchTerms) -> ColumnElement[bool]:
    """Its reading for the profile's location says something the profile rules out. Only
    what is known counts: an offer not read, or a NULL answer, contradicts nothing."""
    reasons = [OfferReadingRow.stable.is_(False)]
    if terms.work_modes:
        reasons.append(OfferReadingRow.work_mode.not_in(terms.work_modes))
    if terms.location is not None:
        reasons.append(OfferReadingRow.admits_location.is_(False))
    return exists().where(_read_for(terms.location), or_(*reasons))


def _fits(terms: SearchTerms) -> ColumnElement[bool]:
    return and_(_fits_words(terms), not_(_contradicted(terms)))


def _fits_words(terms: SearchTerms) -> ColumnElement[bool]:
    """A title in the offer's title, every keyword in title or description, no exclusion
    in the title; ignoring case. Exclusions skip the description: a passing mention of an
    excluded word there would drop good offers."""
    text = OfferRow.title + " " + func.coalesce(OfferRow.description, "")
    return and_(
        or_(false(), *(OfferRow.title.icontains(title, autoescape=True) for title in terms.titles)),
        *(text.icontains(keyword, autoescape=True) for keyword in terms.keywords),
        *(
            not_(OfferRow.title.icontains(excluded, autoescape=True))
            for excluded in terms.excluded_keywords
        ),
    )


def filtered(profiles: Sequence[SearchTerms]) -> ColumnElement[bool]:
    """Pending, imported (only those have a description) and fitting no profile."""
    return and_(
        OfferRow.status == OfferStatus.PENDING,
        OfferRow.description.is_not(None),
        not_(or_(false(), *(_fits(terms) for terms in profiles))),
    )


def _select_offers(profiles: Sequence[SearchTerms]) -> Select[OfferRow]:
    # populate_existing: rows already in the session get `filtered` computed again.
    return (
        select(OfferRow)
        .options(with_expression(OfferRow.filtered, filtered(profiles)))
        .execution_options(populate_existing=True)
    )


class OfferRepository:
    """Never commits: the request session does. Every read needs the current search
    profiles, which decide whether each offer is filtered."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, offer: OfferRow, profiles: Sequence[SearchTerms]) -> OfferRow:
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
        return await self._reload(offer, profiles)

    async def get(self, offer_id: UUID, profiles: Sequence[SearchTerms]) -> OfferRow | None:
        found: OfferRow | None = await self._session.scalar(
            _select_offers(profiles).where(OfferRow.id == offer_id)
        )
        return found

    async def save(self, offer: OfferRow, profiles: Sequence[SearchTerms]) -> OfferRow:
        await self._session.flush()
        return await self._reload(offer, profiles)

    async def _reload(self, offer: OfferRow, profiles: Sequence[SearchTerms]) -> OfferRow:
        # Loads what the database computes (created_at, job_board_name, filtered) here, not
        # lazily outside async code.
        reloaded = await self.get(offer.id, profiles)
        assert reloaded is not None
        return reloaded

    async def list_page(  # noqa: PLR0913, PLR0917  # two filters, the page and the profiles
        self,
        status: OfferStatus | None,
        is_filtered: bool | None,
        page: PageParams,
        profiles: Sequence[SearchTerms],
    ) -> tuple[list[OfferRow], int]:
        conditions: list[ColumnElement[bool]] = []
        if status is not None:
            conditions.append(OfferRow.status == status)
        if is_filtered is not None:
            condition = filtered(profiles)
            conditions.append(condition if is_filtered else not_(condition))
        rows = await self._session.scalars(
            _select_offers(profiles)
            .where(*conditions)
            .order_by(OfferRow.created_at.desc(), OfferRow.id.desc())
            .limit(page.limit)
            .offset(page.offset)
        )
        total = await self._session.scalar(
            select(func.count()).select_from(OfferRow).where(*conditions)
        )
        return list(rows), total or 0


class ReadingRepository:
    """What the offers' descriptions say. Never commits: the request session does."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_unread(
        self, profiles: Sequence[SearchTerms], limit: int
    ) -> tuple[list[tuple[OfferRow, str | None]], int]:
        """The oldest readings still to be made, each an offer and a location, and how many
        there are in all. An offer is read for the location of each profile it fits by its
        words, if it is pending and has a description."""
        unread: list[tuple[OfferRow, str | None]] = []
        total = 0
        for location in dict.fromkeys(terms.location for terms in profiles):
            words = [_fits_words(terms) for terms in profiles if terms.location == location]
            conditions = (
                OfferRow.status == OfferStatus.PENDING,
                func.coalesce(OfferRow.description, "") != "",
                or_(*words),
                not_(exists().where(_read_for(location))),
            )
            count = await self._session.scalar(
                select(func.count()).select_from(OfferRow).where(*conditions)
            )
            total += count or 0
            offers = await self._session.scalars(
                select(OfferRow)
                .where(*conditions)
                .order_by(OfferRow.created_at, OfferRow.id)
                .limit(limit - len(unread))
            )
            unread += [(offer, location) for offer in offers]
        return unread, total

    async def add(self, offer_id: UUID, location: str | None, reading: Reading) -> None:
        self._session.add(
            OfferReadingRow(
                offer_id=offer_id,
                location=location,
                work_mode=reading.work_mode,
                work_mode_evidence=reading.work_mode_evidence,
                admits_location=reading.admits_location,
                admits_location_evidence=reading.admits_location_evidence,
                stable=reading.stable,
                stable_evidence=reading.stable_evidence,
            )
        )
        await self._session.flush()


class FeedImportRepository:
    """Offers coming from feeds.

    Never commits: the request session does.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_new(self, offers: Sequence[OfferRow]) -> list[UUID]:
        """Insert the offers that are not duplicates; return the ids of those inserted.

        ON CONFLICT DO NOTHING keeps the UNIQUE constraint as the judge of duplicates
        without aborting the transaction, as a failed flush would.
        """
        if not offers:
            return []
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
        return list(inserted.all())

    async def count_filtered(
        self, offer_ids: Collection[UUID], profiles: Sequence[SearchTerms]
    ) -> int:
        if not offer_ids:
            return 0
        total = await self._session.scalar(
            select(func.count())
            .select_from(OfferRow)
            .where(OfferRow.id.in_(offer_ids), filtered(profiles))
        )
        return total or 0

    async def expire_missing(self, job_board_id: UUID, published_urls: Collection[str]) -> int:
        """Discard as expired the pending offers imported from a job board that its feed no
        longer publishes. Those added by hand (no description) stay."""
        source = and_(OfferRow.job_board_id == job_board_id, OfferRow.description.is_not(None))
        return await self._expire(source, published_urls)

    async def expire_missing_from_board(
        self, watched_company_id: UUID, published_urls: Collection[str]
    ) -> int:
        """Discard as expired the pending offers of a watched company that left its board."""
        return await self._expire(OfferRow.watched_company_id == watched_company_id, published_urls)

    async def _expire(self, source: ColumnElement[bool], published_urls: Collection[str]) -> int:
        result = await self._session.execute(
            update(OfferRow)
            .where(
                source,
                OfferRow.status == OfferStatus.PENDING,
                OfferRow.url.not_in(published_urls),
            )
            .values(status=OfferStatus.DISCARDED, discard_reason=EXPIRED_REASON)
        )
        return cast(CursorResult[Any], result).rowcount


class WatchedCompanyRepository:
    """Watched companies and the offers imported from their boards.

    Never commits: the request session does.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        # Offers from a board are stored like those from a feed.
        self._offers = FeedImportRepository(session)

    async def add_new_offers(self, offers: Sequence[OfferRow]) -> list[UUID]:
        return await self._offers.add_new(offers)

    async def count_filtered(
        self, offer_ids: Collection[UUID], profiles: Sequence[SearchTerms]
    ) -> int:
        return await self._offers.count_filtered(offer_ids, profiles)

    async def expire_missing_offers(self, company_id: UUID, published_urls: Collection[str]) -> int:
        return await self._offers.expire_missing_from_board(company_id, published_urls)

    async def add(self, company: WatchedCompanyRow) -> WatchedCompanyRow:
        detail = f"The company {company.name} is already watched"
        self._session.add(company)
        await flush_checking_unique(self._session, UNIQUE_WATCHED_NAME_INDEX, detail)
        await self._session.refresh(company)  # loads created_at
        return company

    async def get(self, company_id: UUID) -> WatchedCompanyRow | None:
        return await self._session.get(WatchedCompanyRow, company_id)

    async def list_all(self) -> list[WatchedCompanyRow]:
        rows = await self._session.scalars(
            select(WatchedCompanyRow).order_by(
                func.lower(WatchedCompanyRow.name), WatchedCompanyRow.id
            )
        )
        return list(rows)

    async def delete(self, company: WatchedCompanyRow) -> None:
        await self._session.delete(company)
        await self._session.flush()
