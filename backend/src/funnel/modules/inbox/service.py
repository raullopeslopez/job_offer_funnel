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
from funnel.modules.discovery.domain import Feed, ImportMethod, next_import_at
from funnel.modules.discovery.service import JobBoardService, SearchProfileService
from funnel.modules.inbox.alerts import read_alert
from funnel.modules.inbox.ats import BoardReader
from funnel.modules.inbox.domain import (
    BoardUnavailableError,
    EmailAlertNotImportedError,
    FeedCooldownError,
    FeedOffer,
    FeedUnavailableError,
    ImportedByEmailError,
    JobBoardNotImportedError,
    OfferAction,
    OfferStatus,
    duplicate_key,
    next_status,
)
from funnel.modules.inbox.feeds import FeedReader
from funnel.modules.inbox.models import OfferRow, WatchedCompanyRow
from funnel.modules.inbox.repository import (
    FeedImportRepository,
    OfferRepository,
    WatchedCompanyRepository,
)
from funnel.modules.inbox.schemas import OfferCreate, WatchedCompanyCreate


class OfferService:
    """Status rules come from the domain; promoting goes through the other modules' services.
    The search profiles decide which offers are filtered."""

    def __init__(  # noqa: PLR0913, PLR0917  # one collaborator each, wired in the router
        self,
        repository: OfferRepository,
        profiles: SearchProfileService,
        companies: CompanyService,
        applications: ApplicationService,
    ) -> None:
        self._repository = repository
        self._profiles = profiles
        self._companies = companies
        self._applications = applications

    async def create(self, offer: OfferCreate) -> OfferRow:
        row = OfferRow(
            **offer.model_dump(),
            duplicate_key=duplicate_key(offer.company, offer.title),
            status=OfferStatus.PENDING,
        )
        return await self._repository.add(row, await self._profiles.all_terms())

    async def get(self, offer_id: UUID) -> OfferRow:
        offer = await self._repository.get(offer_id, await self._profiles.all_terms())
        if offer is None:
            raise NotFoundError(f"Offer {offer_id} does not exist")
        return offer

    async def list_page(
        self, status: OfferStatus | None, filtered: bool | None, page: PageParams
    ) -> tuple[list[OfferRow], int]:
        profiles = await self._profiles.all_terms()
        return await self._repository.list_page(status, filtered, page, profiles)

    async def discard(self, offer_id: UUID, reason: str | None) -> OfferRow:
        offer = await self.get(offer_id)
        offer.status = next_status(offer.status, OfferAction.DISCARD)
        offer.discard_reason = reason
        return await self._repository.save(offer, await self._profiles.all_terms())

    async def restore(self, offer_id: UUID) -> None:
        offer = await self.get(offer_id)
        offer.status = next_status(offer.status, OfferAction.RESTORE)
        offer.discard_reason = None
        await self._repository.save(offer, await self._profiles.all_terms())

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
        return await self._repository.save(offer, await self._profiles.all_terms())


@dataclass(frozen=True)
class ImportResult:
    job_board_id: UUID
    found: int
    added: int
    filtered: int
    expired: int
    imported_at: datetime


class FeedImportService:
    """Reads the feed of a job board and fills the inbox, within the limits of the feed's
    terms."""

    def __init__(  # noqa: PLR0913, PLR0917  # one collaborator each, wired in the router
        self,
        imports: FeedImportRepository,
        profiles: SearchProfileService,
        job_boards: JobBoardService,
        reader: FeedReader,
    ) -> None:
        self._imports = imports
        self._profiles = profiles
        self._job_boards = job_boards
        self._reader = reader

    async def import_job_board(self, job_board_id: UUID, now: datetime) -> ImportResult:
        job_board = await self._job_boards.get(job_board_id)
        if job_board.import_method is ImportMethod.NONE:
            raise JobBoardNotImportedError(f"The job board {job_board.name} is not imported")
        if job_board.import_method is ImportMethod.EMAIL:
            raise ImportedByEmailError(f"{job_board.name} is imported from its email alerts")
        last = job_board.last_imported_at
        if last is not None and now < next_import_at(last):
            raise FeedCooldownError(job_board.name, next_import_at(last), now)

        profiles = await self._profiles.all_terms()
        titles = list(dict.fromkeys(title for terms in profiles for title in terms.titles))
        try:
            published = await self._read(job_board.feed, job_board.rss_url_template, titles)
        except (httpx2.HTTPError, ValueError, KeyError, TypeError) as error:
            # Network failure, error status or an unexpected shape: the source is unusable now.
            raise FeedUnavailableError(f"{job_board.name} could not be read") from error
        added = await self._imports.add_new(
            [_offer_row(offer, job_board_id=job_board.id) for offer in published]
        )
        filtered = await self._imports.count_filtered(added, profiles)
        expired = await self._imports.expire_missing(
            job_board.id, [offer.url for offer in published]
        )
        # Only a successful read counts for the limit: a failed one can be retried at once.
        await self._job_boards.record_import(job_board, now)
        return ImportResult(job_board.id, len(published), len(added), filtered, expired, now)

    async def _read(
        self, feed: Feed | None, rss_url_template: str | None, titles: list[str]
    ) -> list[FeedOffer]:
        if feed is not None:
            return await self._reader.read(feed, titles)
        # The schemas and a CHECK give every imported job board a feed or an RSS.
        assert rss_url_template is not None
        return await self._reader.read_rss(rss_url_template, titles)


@dataclass(frozen=True)
class AlertImportResult:
    job_board_id: UUID
    found: int
    added: int
    filtered: int
    imported_at: datetime


class EmailAlertService:
    """Imports the offers of a job alert email into the job board that imports the alert.

    No limit and no expiry: each alert is a new email that lists only new offers.
    """

    def __init__(
        self,
        imports: FeedImportRepository,
        profiles: SearchProfileService,
        job_boards: JobBoardService,
    ) -> None:
        self._imports = imports
        self._profiles = profiles
        self._job_boards = job_boards

    async def import_alert(self, sender: str, text: str, now: datetime) -> AlertImportResult:
        email_alert, offers = read_alert(sender, text)
        job_board = await self._job_boards.find_by_email_alert(email_alert)
        if job_board is None:
            raise EmailAlertNotImportedError(f"No job board imports the {email_alert} alerts")
        added = await self._imports.add_new(
            [_offer_row(offer, job_board_id=job_board.id) for offer in offers]
        )
        filtered = await self._imports.count_filtered(added, await self._profiles.all_terms())
        return AlertImportResult(job_board.id, len(offers), len(added), filtered, now)


@dataclass(frozen=True)
class BoardImportResult:
    watched_company_id: UUID
    found: int
    added: int
    filtered: int
    expired: int
    imported_at: datetime


class WatchedCompanyService:
    """Watched companies, and importing their ATS boards into the inbox (no rate limit)."""

    def __init__(
        self,
        companies: WatchedCompanyRepository,
        profiles: SearchProfileService,
        reader: BoardReader,
    ) -> None:
        self._companies = companies
        self._profiles = profiles
        self._reader = reader

    async def create(self, company: WatchedCompanyCreate) -> WatchedCompanyRow:
        return await self._companies.add(WatchedCompanyRow(**company.model_dump()))

    async def list_all(self) -> list[WatchedCompanyRow]:
        return await self._companies.list_all()

    async def get(self, company_id: UUID) -> WatchedCompanyRow:
        company = await self._companies.get(company_id)
        if company is None:
            raise NotFoundError(f"Watched company {company_id} does not exist")
        return company

    async def delete(self, company_id: UUID) -> None:
        await self._companies.delete(await self.get(company_id))

    async def import_board(self, company_id: UUID, now: datetime) -> BoardImportResult:
        company = await self.get(company_id)
        published = await self._read(company)
        added = await self._companies.add_new_offers(
            [_offer_row(offer, watched_company_id=company.id) for offer in published]
        )
        filtered = await self._companies.count_filtered(added, await self._profiles.all_terms())
        expired = await self._companies.expire_missing_offers(
            company.id, [offer.url for offer in published]
        )
        return BoardImportResult(company.id, len(published), len(added), filtered, expired, now)

    async def _read(self, company: WatchedCompanyRow) -> list[FeedOffer]:
        try:
            return await self._reader.read(company.ats, company.board, company.name)
        except (httpx2.HTTPError, ValueError, KeyError, TypeError) as error:
            # Network failure, error status (404: unknown board) or an unexpected shape.
            raise BoardUnavailableError(
                f"The {company.ats} board {company.board} could not be read"
            ) from error


def _offer_row(
    offer: FeedOffer, *, job_board_id: UUID | None = None, watched_company_id: UUID | None = None
) -> OfferRow:
    return OfferRow(
        url=offer.url,
        company=offer.company,
        title=offer.title,
        description=offer.description,
        duplicate_key=duplicate_key(offer.company, offer.title),
        status=OfferStatus.PENDING,
        job_board_id=job_board_id,
        watched_company_id=watched_company_id,
    )
