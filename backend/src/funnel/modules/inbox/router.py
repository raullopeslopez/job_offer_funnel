from http import HTTPStatus
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from funnel.core.clock import Clock, get_clock
from funnel.core.db import get_session
from funnel.core.errors import ProblemRead, ValidationProblemRead
from funnel.core.pagination import Page, PageParams, get_page_params
from funnel.modules.applications.service import build_application_service
from funnel.modules.companies.service import build_company_service
from funnel.modules.inbox.domain import OfferStatus
from funnel.modules.inbox.repository import OfferRepository
from funnel.modules.inbox.schemas import (
    DiscardCreate,
    FeedRead,
    ImportCreate,
    ImportRead,
    OfferCreate,
    OfferRead,
    PromotionCreate,
)
from funnel.modules.inbox.service import OfferService

offers_router = APIRouter(prefix="/offers", tags=["inbox"])


def get_offer_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> OfferService:
    # Composition root. One session for all three services: promoting is all or nothing.
    return OfferService(
        OfferRepository(session),
        build_company_service(session),
        build_application_service(session, clock),
    )


Service = Annotated[OfferService, Depends(get_offer_service)]

_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    HTTPStatus.NOT_FOUND: {"model": ProblemRead, "description": "Offer does not exist"}
}
_WRONG_STATUS: dict[int | str, dict[str, Any]] = {
    HTTPStatus.CONFLICT: {
        "model": ProblemRead,
        "description": "Not allowed in the offer's current status (`invalid-offer-status`)",
    }
}


@offers_router.post(
    "",
    status_code=HTTPStatus.CREATED,
    responses={
        HTTPStatus.CONFLICT: {
            "model": ProblemRead,
            "description": "An offer with the same company and title already exists, "
            "even if discarded (`already-exists`)",
        },
        HTTPStatus.UNPROCESSABLE_CONTENT: {
            "model": ValidationProblemRead | ProblemRead,
            "description": "Invalid body (`validation-error`), or the job board does not "
            "exist (`unknown-job-board`)",
        },
    },
)
async def create_offer(offer: OfferCreate, service: Service) -> OfferRead:
    """Add an offer to the inbox, as pending. Company and title identify it."""
    created = await service.create(offer)
    return OfferRead.model_validate(created, from_attributes=True)


@offers_router.get("")
async def list_offers(
    page: Annotated[PageParams, Depends(get_page_params)],
    service: Service,
    status: Annotated[OfferStatus | None, Query()] = None,
) -> Page[OfferRead]:
    """Offers from the most recently added."""
    offers, total = await service.list_page(status, page)
    return Page(
        items=[OfferRead.model_validate(row, from_attributes=True) for row in offers],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@offers_router.get("/{offer_id}", responses=_NOT_FOUND)
async def read_offer(offer_id: UUID, service: Service) -> OfferRead:
    offer = await service.get(offer_id)
    return OfferRead.model_validate(offer, from_attributes=True)


@offers_router.post(
    "/{offer_id}/discard",
    status_code=HTTPStatus.CREATED,
    responses={**_NOT_FOUND, **_WRONG_STATUS},
)
async def discard_offer(offer_id: UUID, discard: DiscardCreate, service: Service) -> OfferRead:
    """Discard a pending offer, with an optional reason."""
    discarded = await service.discard(offer_id, discard.reason)
    return OfferRead.model_validate(discarded, from_attributes=True)


@offers_router.delete(
    "/{offer_id}/discard",
    status_code=HTTPStatus.NO_CONTENT,
    responses={**_NOT_FOUND, **_WRONG_STATUS},
)
async def restore_offer(offer_id: UUID, service: Service) -> None:
    """Undo the discard: the offer is pending again."""
    await service.restore(offer_id)


@offers_router.post(
    "/{offer_id}/promotion",
    status_code=HTTPStatus.CREATED,
    responses={**_NOT_FOUND, **_WRONG_STATUS},
)
async def promote_offer(offer_id: UUID, promotion: PromotionCreate, service: Service) -> OfferRead:
    """Turn a pending offer into an application in `evaluated`.

    The application uses the company with the offer's company name, ignoring case,
    or a new one; the title becomes the role and the offer's URL is kept.
    """
    promoted = await service.promote(offer_id, promotion.channel)
    return OfferRead.model_validate(promoted, from_attributes=True)


# --- Public feeds ---

feeds_router = APIRouter(prefix="/feeds", tags=["inbox"])


@feeds_router.get("")
async def list_feeds(service: Service) -> list[FeedRead]:
    """Every public feed, with its last import and the earliest next one."""
    raise NotImplementedError


@feeds_router.post(
    "/{feed}/imports",
    status_code=HTTPStatus.CREATED,
    responses={
        HTTPStatus.NOT_FOUND: {"model": ProblemRead, "description": "Feed does not exist"},
        HTTPStatus.UNPROCESSABLE_CONTENT: {
            "model": ValidationProblemRead | ProblemRead,
            "description": "Invalid body (`validation-error`), or the search profile does "
            "not exist (`unknown-search-profile`)",
        },
        HTTPStatus.TOO_MANY_REQUESTS: {
            "model": ProblemRead,
            "description": "Imported less than 6 hours ago (`feed-cooldown`); "
            "`Retry-After` gives the seconds to wait",
        },
        HTTPStatus.BAD_GATEWAY: {
            "model": ProblemRead,
            "description": "The feed did not answer (`feed-unavailable`); nothing changed",
        },
    },
)
async def import_feed(feed: str, body: ImportCreate, service: Service) -> ImportRead:
    """Add the feed's offers that match the profile to the inbox, as pending.

    Duplicates are skipped; pending offers of this feed that left it are discarded as
    expired. A feed can be imported at most once every 6 hours (each feed's terms).
    """
    raise NotImplementedError


router = APIRouter()
router.include_router(offers_router)
router.include_router(feeds_router)
