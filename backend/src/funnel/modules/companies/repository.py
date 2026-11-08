from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from funnel.core.exceptions import AlreadyExistsError
from funnel.core.pagination import PageParams
from funnel.modules.companies.models import UNIQUE_NAME_INDEX, CompanyRow


class CompanyRepository:
    """Never commits: the request session does."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, company: CompanyRow) -> CompanyRow:
        self._session.add(company)
        try:
            # Flush now so a duplicate name surfaces here as a business error, not at commit.
            await self._session.flush()
        except IntegrityError as error:
            if UNIQUE_NAME_INDEX in str(error.orig):
                raise AlreadyExistsError(
                    f"A company named {company.name} already exists"
                ) from error
            raise
        return company

    async def get(self, company_id: UUID) -> CompanyRow | None:
        return await self._session.get(CompanyRow, company_id)

    async def list_page(self, page: PageParams) -> tuple[list[CompanyRow], int]:
        rows = await self._session.scalars(
            select(CompanyRow)
            .order_by(func.lower(CompanyRow.name), CompanyRow.id)
            .limit(page.limit)
            .offset(page.offset)
        )
        total = await self._session.scalar(select(func.count()).select_from(CompanyRow))
        return list(rows), total or 0
