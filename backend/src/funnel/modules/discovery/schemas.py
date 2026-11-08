from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, Field, StringConstraints, field_validator

from funnel.modules.discovery.domain import WorkMode

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


def _keep_first_ignoring_case[ItemT: str](items: list[ItemT]) -> list[ItemT]:
    """Drop repeated items, ignoring case, keeping the first one and the order."""
    seen: set[str] = set()
    kept: list[ItemT] = []
    for item in items:
        if item.casefold() not in seen:
            seen.add(item.casefold())
            kept.append(item)
    return kept


Words = Annotated[list[Text], AfterValidator(_keep_first_ignoring_case)]
Titles = Annotated[Words, Field(min_length=1, examples=[["Backend Engineer", "Python Developer"]])]
WorkModes = Annotated[
    list[WorkMode],
    AfterValidator(_keep_first_ignoring_case),
    Field(description="Accepted work modes; empty means any."),
]


class SearchProfileCreate(BaseModel):
    name: Text
    titles: Titles = Field(description="Job titles; any of them may match.")
    keywords: Words = Field(default=[], description="All of them must appear.")
    excluded_keywords: Words = Field(default=[], description="None of them may appear.")
    location: Text | None = None
    work_modes: WorkModes = []


class SearchProfileUpdate(BaseModel):
    """Partial update: only the fields sent change. `[]` clears a list, `null` the location."""

    name: Text | None = None
    titles: Titles | None = None
    keywords: Words | None = None
    excluded_keywords: Words | None = None
    location: Text | None = None
    work_modes: WorkModes | None = None

    @field_validator("name", "titles", "keywords", "excluded_keywords", "work_modes")
    @classmethod
    def _reject_null(cls, value: object) -> object:
        # Runs only for fields sent in the body: lists are cleared with [], never null.
        if value is None:
            msg = "cannot be null"
            raise ValueError(msg)
        return value


class SearchProfileRead(BaseModel):
    id: UUID
    name: str
    titles: list[str]
    keywords: list[str]
    excluded_keywords: list[str]
    location: str | None
    work_modes: list[WorkMode]
