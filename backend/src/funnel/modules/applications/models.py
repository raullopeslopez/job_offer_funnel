from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid7

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text, column, func, select, table
from sqlalchemy.orm import Mapped, column_property, mapped_column

from funnel.core.db import Base
from funnel.modules.applications.domain import Channel, Outcome, Priority, Stage


def _enum_column_type(enum: type[StrEnum], column: str) -> Enum:
    # VARCHAR + CHECK instead of a native PG enum: adding a value needs no type migration.
    # One instance per column so each CHECK constraint gets its own name.
    return Enum(
        enum,
        native_enum=False,
        create_constraint=True,
        length=32,
        name=column,
        values_callable=lambda members: [member.value for member in members],
    )


# Its violation means "the company does not exist": the repository translates it.
COMPANY_FOREIGN_KEY = "fk_applications_company_id_companies"

# A lightweight view of the companies table, by name: not a model, so nothing is imported
# from the companies module and Alembic does not see a second definition of the table.
_companies = table("companies", column("id"), column("name"))


class ApplicationRow(Base):
    __tablename__ = "applications"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    # Referenced by table name only: modules never import each other's models.
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT", name=COMPANY_FOREIGN_KEY), index=True
    )
    role: Mapped[str] = mapped_column(String(200))
    channel: Mapped[Channel] = mapped_column(_enum_column_type(Channel, "channel"))
    priority: Mapped[Priority | None] = mapped_column(_enum_column_type(Priority, "priority"))
    url: Mapped[str | None] = mapped_column(String(2048))
    notes: Mapped[str | None] = mapped_column(Text)
    stage: Mapped[Stage] = mapped_column(_enum_column_type(Stage, "stage"))
    outcome: Mapped[Outcome | None] = mapped_column(_enum_column_type(Outcome, "outcome"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Loaded with every query, so responses always show the company's current name.
    company_name: Mapped[str] = column_property(
        select(_companies.c.name).where(_companies.c.id == company_id).scalar_subquery()
    )


class TransitionRow(Base):
    __tablename__ = "transitions"

    # UUIDv7 ids are time-ordered: they break ties between transitions on the same day.
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    application_id: Mapped[UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    from_stage: Mapped[Stage | None] = mapped_column(_enum_column_type(Stage, "from_stage"))
    to_stage: Mapped[Stage] = mapped_column(_enum_column_type(Stage, "to_stage"))
    outcome: Mapped[Outcome | None] = mapped_column(_enum_column_type(Outcome, "outcome"))
    occurred_on: Mapped[date] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(Text)
