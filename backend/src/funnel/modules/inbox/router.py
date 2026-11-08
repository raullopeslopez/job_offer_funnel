from http import HTTPStatus
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from funnel.core.db import get_session
from funnel.core.errors import ProblemRead, ValidationProblemRead
from funnel.core.pagination import Page, PageParams, get_page_params
from funnel.modules.inbox.domain import OfferStatus
from funnel.modules.inbox.repository import OfferRepository
from funnel.modules.inbox.schemas import DiscardCreate, OfferCreate, OfferRead, PromotionCreate
from funnel.modules.inbox.service import OfferService

router = APIRouter(prefix="/offers", tags=["inbox"])


def get_offer_service(session: Annotated[AsyncSession, Depends(get_session)]) -> OfferService:
    # Composition root: the only place in the router that knows about the repository.
    return OfferService(OfferRepository(session))


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


@router.post(
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
    raise NotImplementedError


@router.get("")
async def list_offers(
    page: Annotated[PageParams, Depends(get_page_params)],
    service: Service,
    status: Annotated[OfferStatus | None, Query()] = None,
) -> Page[OfferRead]:
    """Offers from the most recently added."""
    raise NotImplementedError


@router.get("/{offer_id}", responses=_NOT_FOUND)
async def read_offer(offer_id: UUID, service: Service) -> OfferRead:
    raise NotImplementedError


@router.post(
    "/{offer_id}/discard",
    status_code=HTTPStatus.CREATED,
    responses={**_NOT_FOUND, **_WRONG_STATUS},
)
async def discard_offer(offer_id: UUID, discard: DiscardCreate, service: Service) -> OfferRead:
    """Discard a pending offer, with an optional reason."""
    raise NotImplementedError


@router.delete(
    "/{offer_id}/discard",
    status_code=HTTPStatus.NO_CONTENT,
    responses={**_NOT_FOUND, **_WRONG_STATUS},
)
async def restore_offer(offer_id: UUID, service: Service) -> None:
    """Undo the discard: the offer is pending again."""
    raise NotImplementedError


@router.post(
    "/{offer_id}/promotion",
    status_code=HTTPStatus.CREATED,
    responses={**_NOT_FOUND, **_WRONG_STATUS},
)
async def promote_offer(offer_id: UUID, promotion: PromotionCreate, service: Service) -> OfferRead:
    """Turn a pending offer into an application in `evaluated`.

    The application uses the company with the offer's company name, ignoring case,
    or a new one; the title becomes the role and the offer's URL is kept.
    """
    raise NotImplementedError
