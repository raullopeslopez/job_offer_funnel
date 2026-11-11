from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid7

from sqlalchemy import ARRAY, CheckConstraint, DateTime, Enum, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from funnel.core.db import Base
from funnel.modules.discovery.domain import Feed, ImportMethod, Syntax, WorkMode, next_import_at

UNIQUE_PROFILE_NAME_INDEX = "uq_search_profiles_lower_name"
UNIQUE_JOB_BOARD_NAME_INDEX = "uq_job_boards_lower_name"
UNIQUE_JOB_BOARD_FEED = "uq_job_boards_feed"

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


def _enum_column_type(enum: type[StrEnum], column: str) -> Enum:
    # VARCHAR + CHECK, like every enum column (see applications/models.py).
    return Enum(
        enum,
        native_enum=False,
        create_constraint=True,
        length=32,
        name=column,
        values_callable=lambda members: [member.value for member in members],
    )


class JobBoardRow(Base):
    __tablename__ = "job_boards"
    __table_args__ = (
        # The schemas validate it first; the database keeps it true whatever writes the row.
        CheckConstraint("(import_method = 'api') = (feed IS NOT NULL)", name="feed_with_api"),
        CheckConstraint(
            "(import_method = 'rss') = (rss_url_template IS NOT NULL)",
            name="rss_url_template_with_rss",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(String(200))
    search_url_template: Mapped[str] = mapped_column(String(2048))
    syntax: Mapped[Syntax] = mapped_column(_enum_column_type(Syntax, "syntax"))
    import_method: Mapped[ImportMethod] = mapped_column(
        _enum_column_type(ImportMethod, "import_method"), default=ImportMethod.NONE
    )
    # Unique: each feed is imported by one job board at most.
    feed: Mapped[Feed | None] = mapped_column(_enum_column_type(Feed, "feed"), unique=True)
    rss_url_template: Mapped[str | None] = mapped_column(String(2048))
    # The 6-hour limit of the feeds' terms is checked against it.
    last_imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def next_import_at(self) -> datetime | None:
        return None if self.last_imported_at is None else next_import_at(self.last_imported_at)


Index(UNIQUE_JOB_BOARD_NAME_INDEX, func.lower(JobBoardRow.name), unique=True)
