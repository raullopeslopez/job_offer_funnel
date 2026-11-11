from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid7

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, column, func, select, table
from sqlalchemy.orm import Mapped, column_property, mapped_column, query_expression

from funnel.core.db import Base
from funnel.modules.inbox.domain import Ats, OfferStatus

UNIQUE_DUPLICATE_KEY = "uq_offers_duplicate_key"
UNIQUE_WATCHED_NAME_INDEX = "uq_watched_companies_lower_name"
# Their violation means "the job board does not exist": the repository translates it.
JOB_BOARD_FOREIGN_KEY = "fk_offers_job_board_id_job_boards"

# Other modules' tables by name only: modules never import each other's models.
_job_boards = table("job_boards", column("id"), column("name"))


def _enum_column_type(enum: type[StrEnum], column: str) -> Enum:
    # VARCHAR + CHECK, one instance per column (see applications/models.py).
    return Enum(
        enum,
        native_enum=False,
        create_constraint=True,
        length=32,
        name=column,
        values_callable=lambda members: [member.value for member in members],
    )


class WatchedCompanyRow(Base):
    """A company whose ATS job board is read on demand."""

    __tablename__ = "watched_companies"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(String(200))
    ats: Mapped[Ats] = mapped_column(_enum_column_type(Ats, "ats"))
    board: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# Unique ignoring case, enforced by the database (see companies/models.py).
Index(UNIQUE_WATCHED_NAME_INDEX, func.lower(WatchedCompanyRow.name), unique=True)


class OfferRow(Base):
    __tablename__ = "offers"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    url: Mapped[str] = mapped_column(String(2048))
    company: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(200))
    # Only imported offers have one (maybe empty): it is what marks them as imported, and
    # their keywords are looked for in it.
    description: Mapped[str | None] = mapped_column(Text)
    # Company and title normalized: the database rejects the same offer twice.
    duplicate_key: Mapped[str] = mapped_column(String(401), unique=True)
    # Where it was found by hand, or the job board it was imported from.
    job_board_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("job_boards.id", ondelete="RESTRICT", name=JOB_BOARD_FOREIGN_KEY), index=True
    )
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[OfferStatus] = mapped_column(_enum_column_type(OfferStatus, "status"))
    discard_reason: Mapped[str | None] = mapped_column(String(200))
    application_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("applications.id", ondelete="SET NULL"), index=True
    )
    # Stopping watching a company keeps its offers, without a source.
    watched_company_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("watched_companies.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Depends on the current search profiles, so every query computes it (see repository.py).
    filtered: Mapped[bool] = query_expression()
    watched_company_name: Mapped[str | None] = column_property(
        select(WatchedCompanyRow.name)
        .where(WatchedCompanyRow.id == watched_company_id)
        .scalar_subquery()
    )
    job_board_name: Mapped[str | None] = column_property(
        select(_job_boards.c.name).where(_job_boards.c.id == job_board_id).scalar_subquery()
    )
