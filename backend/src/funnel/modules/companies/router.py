from http import HTTPStatus
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends

from funnel.core.errors import ProblemRead
from funnel.core.pagination import Page, PageParams, get_page_params
from funnel.modules.companies.schemas import CompanyCreate, CompanyRead

router = APIRouter(prefix="/companies", tags=["companies"])

_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    HTTPStatus.NOT_FOUND: {"model": ProblemRead, "description": "Company does not exist"}
}


@router.post(
    "",
    status_code=HTTPStatus.CREATED,
    responses={
        HTTPStatus.CONFLICT: {
            "model": ProblemRead,
            "description": "A company with that name already exists (`already-exists`)",
        }
    },
)
async def create_company(company: CompanyCreate) -> CompanyRead:
    """Create a company. Names are unique ignoring case and surrounding spaces."""
    raise NotImplementedError


@router.get("/{company_id}", responses=_NOT_FOUND)
async def read_company(company_id: UUID) -> CompanyRead:
    raise NotImplementedError


@router.get("")
async def list_companies(
    page: Annotated[PageParams, Depends(get_page_params)],
) -> Page[CompanyRead]:
    """Companies in alphabetical order, ignoring case."""
    raise NotImplementedError
