from datetime import datetime
from uuid import UUID, uuid7

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, column, func, select, table
from sqlalchemy.orm import Mapped, column_property, mapped_column

from funnel.core.db import Base
from funnel.modules.inbox.domain import OfferStatus

UNIQUE_DUPLICATE_KEY = "uq_offers_duplicate_key"
# Their violation means "the job board does not exist": the repository translates it.
JOB_BOARD_FOREIGN_KEY = "fk_offers_job_board_id_job_boards"

# Other modules' tables by name only: modules never import each other's models.
_job_boards = table("job_boards", column("id"), column("name"))


class OfferRow(Base):
    __tablename__ = "offers"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    url: Mapped[str] = mapped_column(String(2048))
    company: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(200))
    # Company and title normalized: the database rejects the same offer twice.
    duplicate_key: Mapped[str] = mapped_column(String(401), unique=True)
    job_board_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("job_boards.id", ondelete="RESTRICT", name=JOB_BOARD_FOREIGN_KEY), index=True
    )
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[OfferStatus] = mapped_column(
        Enum(
            OfferStatus,
            native_enum=False,
            create_constraint=True,
            length=32,
            name="status",
            values_callable=lambda members: [member.value for member in members],
        )
    )
    discard_reason: Mapped[str | None] = mapped_column(String(200))
    application_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("applications.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    job_board_name: Mapped[str | None] = column_property(
        select(_job_boards.c.name).where(_job_boards.c.id == job_board_id).scalar_subquery()
    )
