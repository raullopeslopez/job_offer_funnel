from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid7

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    column,
    func,
    select,
    table,
    text,
)
from sqlalchemy.orm import (
    Mapped,
    column_property,
    mapped_column,
    query_expression,
    relationship,
)

from funnel.core.db import Base
from funnel.modules.discovery.domain import WorkMode
from funnel.modules.inbox.domain import Ats, DiscardReason, FilterReason, OfferStatus, Review

UNIQUE_DUPLICATE_KEY = "uq_offers_duplicate_key"
UNIQUE_WATCHED_NAME_INDEX = "uq_watched_companies_lower_name"
UNIQUE_READING_INDEX = "uq_offer_readings_offer_id_location"
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


class OfferReadingRow(Base):
    """What an offer's description says, read for the location of a search profile (NULL
    for profiles without one). NULL answers are what the description does not say."""

    __tablename__ = "offer_readings"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    offer_id: Mapped[UUID] = mapped_column(ForeignKey("offers.id", ondelete="CASCADE"))
    location: Mapped[str | None] = mapped_column(String(200))
    work_mode: Mapped[WorkMode | None] = mapped_column(_enum_column_type(WorkMode, "work_mode"))
    work_mode_evidence: Mapped[str | None] = mapped_column(Text)
    admits_location: Mapped[bool | None] = mapped_column(Boolean)
    admits_location_evidence: Mapped[str | None] = mapped_column(Text)
    stable: Mapped[bool | None] = mapped_column(Boolean)
    stable_evidence: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# One reading per offer and location, the one without a location included. It is also the
# index of the foreign key: offer_id leads it.
Index(
    UNIQUE_READING_INDEX,
    OfferReadingRow.offer_id,
    OfferReadingRow.location,
    unique=True,
    postgresql_nulls_not_distinct=True,
)


class OfferRow(Base):
    __tablename__ = "offers"
    __allow_unmapped__ = True  # filter_reason

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
    discard_reason: Mapped[DiscardReason | None] = mapped_column(
        _enum_column_type(DiscardReason, "discard_reason")
    )
    discard_word: Mapped[str | None] = mapped_column(String(200))
    # Set when a filtered offer is promoted (a rescue) or marked rightly filtered, with
    # the rules that filtered it then: they say whether it was a near miss.
    review: Mapped[Review | None] = mapped_column(_enum_column_type(Review, "review"))
    review_rules: Mapped[list[str]] = mapped_column(ARRAY(String(32)), server_default=text("'{}'"))
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
    # Not a column: it depends on the current search profiles, and the repository sets it
    # on each read, for pending imported offers.
    filter_reason: FilterReason | None = None
    readings: Mapped[list[OfferReadingRow]] = relationship(
        lazy="selectin", order_by=(OfferReadingRow.created_at, OfferReadingRow.id), viewonly=True
    )
