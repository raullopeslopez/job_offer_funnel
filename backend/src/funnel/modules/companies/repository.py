from collections.abc import Mapping
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from funnel.core.db import flush_checking_references, flush_checking_unique
from funnel.core.pagination import PageParams
from funnel.modules.companies.models import UNIQUE_NAME_INDEX, CompanyRow


class CompanyRepository:
    """Never commits: the request session does."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, company: CompanyRow) -> CompanyRow:
        self._session.add(company)
        await self._flush_checking_name(company)
        return company

    async def get(self, company_id: UUID) -> CompanyRow | None:
        return await self._session.get(CompanyRow, company_id)

    async def find_by_name(self, name: str) -> CompanyRow | None:
        # Same comparison as the unique index: lower(name), surrounding spaces ignored.
        return await self._session.scalar(
            select(CompanyRow).where(func.lower(CompanyRow.name) == name.strip().lower())
        )

    async def update(self, company: CompanyRow, changes: Mapping[str, object]) -> CompanyRow:
        for name, value in changes.items():
            setattr(company, name, value)
        await self._flush_checking_name(company)
        return company

    async def delete(self, company: CompanyRow) -> None:
        # Applications reference companies with ON DELETE RESTRICT.
        detail = f"Company {company.id} still has applications"
        await self._session.delete(company)
        await flush_checking_references(self._session, detail)

    async def list_page(self, page: PageParams) -> tuple[list[CompanyRow], int]:
        rows = await self._session.scalars(
            select(CompanyRow)
            .order_by(func.lower(CompanyRow.name), CompanyRow.id)
            .limit(page.limit)
            .offset(page.offset)
        )
        total = await self._session.scalar(select(func.count()).select_from(CompanyRow))
        return list(rows), total or 0

    async def _flush_checking_name(self, company: CompanyRow) -> None:
        detail = f"A company named {company.name} already exists"
        await flush_checking_unique(self._session, UNIQUE_NAME_INDEX, detail)
