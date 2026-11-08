from http import HTTPStatus
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from funnel.core.db import get_session
from funnel.core.errors import ProblemRead
from funnel.core.pagination import Page, PageParams, get_page_params
from funnel.modules.companies.repository import CompanyRepository
from funnel.modules.companies.schemas import CompanyCreate, CompanyRead
from funnel.modules.companies.service import CompanyService

router = APIRouter(prefix="/companies", tags=["companies"])


def get_company_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CompanyService:
    # Composition root: the only place in the router that knows about the repository.
    return CompanyService(CompanyRepository(session))


Service = Annotated[CompanyService, Depends(get_company_service)]

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
async def create_company(company: CompanyCreate, service: Service) -> CompanyRead:
    """Create a company. Names are unique ignoring case and surrounding spaces."""
    created = await service.create(company.name, company.website)
    return CompanyRead.model_validate(created, from_attributes=True)


@router.get("/{company_id}", responses=_NOT_FOUND)
async def read_company(company_id: UUID, service: Service) -> CompanyRead:
    company = await service.get(company_id)
    return CompanyRead.model_validate(company, from_attributes=True)


@router.get("")
async def list_companies(
    page: Annotated[PageParams, Depends(get_page_params)], service: Service
) -> Page[CompanyRead]:
    """Companies in alphabetical order, ignoring case."""
    companies, total = await service.list_page(page)
    return Page(
        items=[CompanyRead.model_validate(company, from_attributes=True) for company in companies],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )
