from collections.abc import AsyncIterator
from http import HTTPStatus
from typing import Annotated, Any
from uuid import UUID

import httpx2
from fastapi import APIRouter, Depends, Query

from funnel.core.clock import Clock, get_clock
from funnel.core.db import SessionDep
from funnel.core.errors import ProblemRead, ValidationProblemRead
from funnel.core.pagination import Page, PageParams, get_page_params
from funnel.modules.applications.service import build_application_service
from funnel.modules.companies.service import build_company_service
from funnel.modules.discovery.service import build_search_profile_service
from funnel.modules.inbox.ats import BoardReader
from funnel.modules.inbox.domain import OfferStatus, next_import_at
from funnel.modules.inbox.feeds import FeedReader
from funnel.modules.inbox.repository import (
    FeedImportRepository,
    OfferRepository,
    WatchedCompanyRepository,
)
from funnel.modules.inbox.schemas import (
    BoardImportRead,
    DiscardCreate,
    FeedRead,
    ImportRead,
    OfferCreate,
    OfferRead,
    PromotionCreate,
    WatchedCompanyCreate,
    WatchedCompanyRead,
)
from funnel.modules.inbox.service import FeedImportService, OfferService, WatchedCompanyService

offers_router = APIRouter(prefix="/offers", tags=["inbox"])


def get_offer_service(
    session: SessionDep,
    clock: Annotated[Clock, Depends(get_clock)],
) -> OfferService:
    # Composition root. One session for all the services: promoting is all or nothing.
    return OfferService(
        OfferRepository(session),
        build_search_profile_service(session),
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
async def list_offers(  # noqa: PLR0913, PLR0917  # FastAPI injects each input as a parameter
    page: Annotated[PageParams, Depends(get_page_params)],
    service: Service,
    status: Annotated[OfferStatus | None, Query()] = None,
    filtered: Annotated[
        bool | None, Query(description="Only the filtered offers (true) or the others (false).")
    ] = None,
) -> Page[OfferRead]:
    """Offers from the most recently added."""
    offers, total = await service.list_page(status, filtered, page)
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

# Identifies the app to the feeds, as their terms expect; no personal data.
USER_AGENT = "job-offer-funnel"
FEED_TIMEOUT_SECONDS = 20


async def get_feed_client() -> AsyncIterator[httpx2.AsyncClient]:
    """HTTP client for the public feeds; tests replace it so they never reach the internet."""
    async with httpx2.AsyncClient(
        timeout=FEED_TIMEOUT_SECONDS, headers={"User-Agent": USER_AGENT}
    ) as client:
        yield client


def get_feed_import_service(
    session: SessionDep,
    client: Annotated[httpx2.AsyncClient, Depends(get_feed_client)],
) -> FeedImportService:
    return FeedImportService(
        FeedImportRepository(session), build_search_profile_service(session), FeedReader(client)
    )


FeedService = Annotated[FeedImportService, Depends(get_feed_import_service)]


@feeds_router.get("")
async def list_feeds(service: FeedService) -> list[FeedRead]:
    """Every public feed, with its last import and the earliest next one."""
    return [
        FeedRead(
            feed=feed,
            last_imported_at=last,
            next_import_at=None if last is None else next_import_at(last),
        )
        for feed, last in await service.last_imports()
    ]


@feeds_router.post(
    "/{feed}/imports",
    status_code=HTTPStatus.CREATED,
    responses={
        HTTPStatus.NOT_FOUND: {"model": ProblemRead, "description": "Feed does not exist"},
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
async def import_feed(
    feed: str, service: FeedService, clock: Annotated[Clock, Depends(get_clock)]
) -> ImportRead:
    """Add every offer of the feed to the inbox, as pending; the ones that fit no search
    profile are filtered. Himalayas is searched by the titles of every profile.

    Duplicates are skipped; pending offers of this feed that left it are discarded as
    expired. A feed can be imported at most once every 6 hours (each feed's terms).
    """
    result = await service.import_feed(feed, clock.now())
    return ImportRead(
        feed=result.feed,
        found=result.found,
        added=result.added,
        filtered=result.filtered,
        already_in_inbox=result.found - result.added,
        expired=result.expired,
        imported_at=result.imported_at,
    )


# --- ATS companies ---

watched_companies_router = APIRouter(prefix="/watched-companies", tags=["inbox"])


def get_watched_company_service(
    session: SessionDep,
    client: Annotated[httpx2.AsyncClient, Depends(get_feed_client)],
) -> WatchedCompanyService:
    # The ATS boards are read with the feeds' client: same User-Agent and timeout.
    return WatchedCompanyService(
        WatchedCompanyRepository(session),
        build_search_profile_service(session),
        BoardReader(client),
    )


WatchedService = Annotated[WatchedCompanyService, Depends(get_watched_company_service)]

_WATCHED_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    HTTPStatus.NOT_FOUND: {"model": ProblemRead, "description": "Watched company does not exist"}
}


@watched_companies_router.post(
    "",
    status_code=HTTPStatus.CREATED,
    responses={
        HTTPStatus.CONFLICT: {
            "model": ProblemRead,
            "description": "A company with that name, ignoring case, is already watched "
            "(`already-exists`)",
        },
    },
)
async def watch_company(
    company: WatchedCompanyCreate, service: WatchedService
) -> WatchedCompanyRead:
    """Watch a company through the public job board of its ATS."""
    created = await service.create(company)
    return WatchedCompanyRead.model_validate(created, from_attributes=True)


@watched_companies_router.get("")
async def list_watched_companies(service: WatchedService) -> list[WatchedCompanyRead]:
    """Every watched company, by name."""
    return [
        WatchedCompanyRead.model_validate(row, from_attributes=True)
        for row in await service.list_all()
    ]


@watched_companies_router.delete(
    "/{watched_company_id}", status_code=HTTPStatus.NO_CONTENT, responses=_WATCHED_NOT_FOUND
)
async def unwatch_company(watched_company_id: UUID, service: WatchedService) -> None:
    """Stop watching a company. Its offers stay in the inbox, with no watched company."""
    await service.delete(watched_company_id)


@watched_companies_router.post(
    "/{watched_company_id}/imports",
    status_code=HTTPStatus.CREATED,
    responses={
        **_WATCHED_NOT_FOUND,
        HTTPStatus.BAD_GATEWAY: {
            "model": ProblemRead,
            "description": "The ATS did not answer or does not know the board "
            "(`board-unavailable`); nothing changed",
        },
    },
)
async def import_watched_company(
    watched_company_id: UUID, service: WatchedService, clock: Annotated[Clock, Depends(get_clock)]
) -> BoardImportRead:
    """Add every open offer of the company to the inbox, as pending; the ones that fit no
    search profile are filtered.

    Duplicates are skipped; pending offers of this company that left its board are
    discarded as expired. No limit on how often: the ATS boards state none.
    """
    result = await service.import_board(watched_company_id, clock.now())
    return BoardImportRead(
        watched_company_id=result.watched_company_id,
        found=result.found,
        added=result.added,
        filtered=result.filtered,
        already_in_inbox=result.found - result.added,
        expired=result.expired,
        imported_at=result.imported_at,
    )


router = APIRouter()
router.include_router(offers_router)
router.include_router(feeds_router)
router.include_router(watched_companies_router)
