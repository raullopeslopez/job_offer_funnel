from datetime import datetime
from uuid import UUID, uuid7

from sqlalchemy import ARRAY, CheckConstraint, DateTime, Enum, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from funnel.core.db import Base
from funnel.modules.discovery.domain import Syntax, WorkMode

UNIQUE_PROFILE_NAME_INDEX = "uq_search_profiles_lower_name"
UNIQUE_JOB_BOARD_NAME_INDEX = "uq_job_boards_lower_name"

_WORK_MODES = ", ".join(f"'{mode.value}'" for mode in WorkMode)


def _words() -> Mapped[list[str]]:
    return mapped_column(ARRAY(String(200)), server_default=text("'{}'"))


class SearchProfileRow(Base):
    __tablename__ = "search_profiles"
    __table_args__ = (
        # An array has no Enum type: the CHECK keeps every element a valid work mode.
        CheckConstraint(f"work_modes <@ ARRAY[{_WORK_MODES}]::varchar[]", name="work_modes"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(String(200))
    titles: Mapped[list[str]] = mapped_column(ARRAY(String(200)))
    keywords: Mapped[list[str]] = _words()
    excluded_keywords: Mapped[list[str]] = _words()
    location: Mapped[str | None] = mapped_column(String(200))
    work_modes: Mapped[list[str]] = mapped_column(ARRAY(String(16)), server_default=text("'{}'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# Same rule as company names: uniqueness ignoring case lives in the database.
Index(UNIQUE_PROFILE_NAME_INDEX, func.lower(SearchProfileRow.name), unique=True)


class JobBoardRow(Base):
    __tablename__ = "job_boards"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(String(200))
    search_url_template: Mapped[str] = mapped_column(String(2048))
    # VARCHAR + CHECK, like every enum column (see applications/models.py).
    syntax: Mapped[Syntax] = mapped_column(
        Enum(
            Syntax,
            native_enum=False,
            create_constraint=True,
            length=32,
            name="syntax",
            values_callable=lambda members: [member.value for member in members],
        )
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


Index(UNIQUE_JOB_BOARD_NAME_INDEX, func.lower(JobBoardRow.name), unique=True)
