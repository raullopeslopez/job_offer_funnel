from datetime import datetime
from uuid import UUID, uuid7

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from funnel.core.db import Base

UNIQUE_NAME_INDEX = "uq_companies_lower_name"


class CompanyRow(Base):
    __tablename__ = "companies"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(String(200))
    website: Mapped[str | None] = mapped_column(String(2048))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# Uniqueness ignoring case is a business rule enforced by the database, not a check in Python:
# two concurrent requests could both pass a "does it exist?" check.
Index(UNIQUE_NAME_INDEX, func.lower(CompanyRow.name), unique=True)
