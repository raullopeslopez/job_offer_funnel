from collections.abc import Mapping
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

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

    async def find_or_create(self, name: str) -> CompanyRow:
        """The company with that name, ignoring case and surrounding spaces, or a new one."""
        company = await self._repository.find_by_name(name)
        return company or await self.create(name.strip(), None)

    async def update(self, company_id: UUID, changes: Mapping[str, object]) -> CompanyRow:
        company = await self.get(company_id)
        return await self._repository.update(company, changes)

    async def delete(self, company_id: UUID) -> None:
        company = await self.get(company_id)
        await self._repository.delete(company)

    async def list_page(self, page: PageParams) -> tuple[list[CompanyRow], int]:
        return await self._repository.list_page(page)


def build_company_service(session: AsyncSession) -> CompanyService:
    """For other modules: the service on their request session, without its repository."""
    return CompanyService(CompanyRepository(session))
