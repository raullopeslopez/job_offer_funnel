from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid7

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from funnel.core.db import Base
from funnel.modules.applications.domain import Outcome, Stage


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


class ApplicationRow(Base):
    __tablename__ = "applications"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    stage: Mapped[Stage] = mapped_column(_enum_column_type(Stage, "stage"))
    outcome: Mapped[Outcome | None] = mapped_column(_enum_column_type(Outcome, "outcome"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


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
