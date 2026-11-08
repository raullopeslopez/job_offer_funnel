from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import httpx2

from funnel.core.exceptions import NotFoundError
from funnel.core.pagination import PageParams
from funnel.modules.applications.domain import Channel
from funnel.modules.applications.schemas import ApplicationCreate
from funnel.modules.applications.service import ApplicationService
from funnel.modules.companies.service import CompanyService
from funnel.modules.discovery.domain import SearchTerms
from funnel.modules.discovery.service import SearchProfileService
from funnel.modules.inbox.domain import (
    Feed,
    FeedCooldownError,
    FeedOffer,
    FeedUnavailableError,
    OfferAction,
    OfferStatus,
    UnknownSearchProfileError,
    duplicate_key,
    matches,
    next_import_at,
    next_status,
)
from funnel.modules.inbox.feeds import FeedReader
from funnel.modules.inbox.models import OfferRow
from funnel.modules.inbox.repository import FeedImportRepository, OfferRepository
from funnel.modules.inbox.schemas import OfferCreate


class OfferService:
    """Status rules come from the domain; promoting goes through the other modules' services."""

    def __init__(
        self,
        repository: OfferRepository,
        companies: CompanyService,
        applications: ApplicationService,
    ) -> None:
        self._repository = repository
        self._companies = companies
        self._applications = applications

    async def create(self, offer: OfferCreate) -> OfferRow:
        row = OfferRow(
            **offer.model_dump(),
            duplicate_key=duplicate_key(offer.company, offer.title),
            status=OfferStatus.PENDING,
        )
        return await self._repository.add(row)

    async def get(self, offer_id: UUID) -> OfferRow:
        offer = await self._repository.get(offer_id)
        if offer is None:
            raise NotFoundError(f"Offer {offer_id} does not exist")
        return offer

    async def list_page(
        self, status: OfferStatus | None, page: PageParams
    ) -> tuple[list[OfferRow], int]:
        return await self._repository.list_page(status, page)

    async def discard(self, offer_id: UUID, reason: str | None) -> OfferRow:
        offer = await self.get(offer_id)
        offer.status = next_status(offer.status, OfferAction.DISCARD)
        offer.discard_reason = reason
        return await self._repository.save(offer)

    async def restore(self, offer_id: UUID) -> None:
        offer = await self.get(offer_id)
        offer.status = next_status(offer.status, OfferAction.RESTORE)
        offer.discard_reason = None
        await self._repository.save(offer)

    async def promote(self, offer_id: UUID, channel: Channel) -> OfferRow:
        offer = await self.get(offer_id)
        status = next_status(offer.status, OfferAction.PROMOTE)
        company = await self._companies.find_or_create(offer.company)
        application = await self._applications.create(
            ApplicationCreate(
                company_id=company.id, role=offer.title, channel=channel, url=offer.url
            )
        )
        offer.status = status
        offer.application_id = application.id
        return await self._repository.save(offer)


@dataclass(frozen=True)
class ImportResult:
    feed: Feed
    found: int
    matching: int
    added: int
    expired: int
    imported_at: datetime


class FeedImportService:
    """Reads a public feed and fills the inbox, within the limits of the feed's terms."""

    def __init__(
        self, imports: FeedImportRepository, profiles: SearchProfileService, reader: FeedReader
    ) -> None:
        self._imports = imports
        self._profiles = profiles
        self._reader = reader

    async def last_imports(self) -> list[tuple[Feed, datetime | None]]:
        last = await self._imports.last_imports()
        return [(feed, last.get(feed)) for feed in sorted(Feed)]

    async def import_feed(self, feed_name: str, profile_id: UUID, now: datetime) -> ImportResult:
        feed = _feed(feed_name)
        terms = await self._terms(profile_id)
        last = (await self._imports.last_imports()).get(feed)
        if last is not None and now < next_import_at(last):
            raise FeedCooldownError(feed, next_import_at(last), now)

        published = await self._read(feed, terms)
        matching = [offer for offer in published if matches(terms, offer)]
        added = await self._imports.add_new([_offer_row(feed, offer) for offer in matching])
        expired = await self._imports.expire_missing(feed, [offer.url for offer in published])
        # Only a successful read counts for the limit: a failed one can be retried at once.
        await self._imports.record(feed, now)
        return ImportResult(feed, len(published), len(matching), added, expired, now)

    async def _terms(self, profile_id: UUID) -> SearchTerms:
        try:
            profile = await self._profiles.get(profile_id)
        except NotFoundError as error:
            raise UnknownSearchProfileError(
                f"Search profile {profile_id} does not exist"
            ) from error
        return SearchTerms(profile.titles, profile.keywords, profile.excluded_keywords)

    async def _read(self, feed: Feed, terms: SearchTerms) -> list[FeedOffer]:
        try:
            return await self._reader.read(feed, terms)
        except (httpx2.HTTPError, ValueError, KeyError, TypeError) as error:
            # Network failure, error status or an unexpected shape: the feed is unusable now.
            raise FeedUnavailableError(f"{feed} could not be read") from error


def _feed(name: str) -> Feed:
    try:
        return Feed(name)
    except ValueError as error:
        raise NotFoundError(f"Feed {name} does not exist") from error


def _offer_row(feed: Feed, offer: FeedOffer) -> OfferRow:
    return OfferRow(
        url=offer.url,
        company=offer.company,
        title=offer.title,
        duplicate_key=duplicate_key(offer.company, offer.title),
        status=OfferStatus.PENDING,
        feed=feed,
    )
