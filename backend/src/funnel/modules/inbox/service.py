from uuid import UUID

from funnel.core.exceptions import NotFoundError
from funnel.core.pagination import PageParams
from funnel.modules.applications.domain import Channel
from funnel.modules.applications.schemas import ApplicationCreate
from funnel.modules.applications.service import ApplicationService
from funnel.modules.companies.service import CompanyService
from funnel.modules.inbox.domain import OfferAction, OfferStatus, duplicate_key, next_status
from funnel.modules.inbox.models import OfferRow
from funnel.modules.inbox.repository import OfferRepository
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
