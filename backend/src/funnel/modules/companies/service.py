from uuid import UUID

from funnel.core.exceptions import NotFoundError
from funnel.core.pagination import PageParams
from funnel.modules.companies.models import CompanyRow
from funnel.modules.companies.repository import CompanyRepository


class CompanyService:
    """CRUD module: works directly with ORM rows (no domain layer)."""

    def __init__(self, repository: CompanyRepository) -> None:
        self._repository = repository

    async def create(self, name: str, website: str | None) -> CompanyRow:
        return await self._repository.add(CompanyRow(name=name, website=website))

    async def get(self, company_id: UUID) -> CompanyRow:
        company = await self._repository.get(company_id)
        if company is None:
            raise NotFoundError(f"Company {company_id} does not exist")
        return company

    async def list_page(self, page: PageParams) -> tuple[list[CompanyRow], int]:
        return await self._repository.list_page(page)
