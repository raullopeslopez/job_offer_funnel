import re
from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    StringConstraints,
    TypeAdapter,
    field_validator,
    model_validator,
)

from funnel.core.fields import HttpUrlText
from funnel.modules.discovery.domain import (
    PLACEHOLDERS,
    QUERY_PLACEHOLDER,
    Feed,
    ImportMethod,
    Syntax,
    WorkMode,
)

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


_PLACEHOLDER = re.compile(r"\{(\w*)\}")
_http_url_text = TypeAdapter(HttpUrlText)


def _validate_search_url_template(template: str) -> str:
    found = set(_PLACEHOLDER.findall(template))
    if QUERY_PLACEHOLDER not in found:
        msg = f"must contain {{{QUERY_PLACEHOLDER}}}"
        raise ValueError(msg)
    if unknown := found - PLACEHOLDERS:
        msg = f"unknown placeholders: {', '.join(sorted(unknown))}"
        raise ValueError(msg)
    # Validate the URL as it will be opened, with the placeholders filled in.
    _http_url_text.validate_python(_PLACEHOLDER.sub("x", template))
    return template


SearchUrlTemplate = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=2048),
    AfterValidator(_validate_search_url_template),
    Field(
        description="http(s) URL with {query} where the search goes, and optionally {location}.",
        examples=["https://www.linkedin.com/jobs/search/?keywords={query}&location={location}"],
    ),
]


_IMPORT_METHOD = Field(
    description="How its offers reach the inbox: `none` (by hand, with its generated "
    "searches) or `api` (imported from its `feed`)."
)
_FEED = Field(
    description="The public feed it is imported from: required with `api`, null with "
    "`none`. At most one job board imports each feed."
)


class JobBoardCreate(BaseModel):
    name: Text
    search_url_template: SearchUrlTemplate
    syntax: Syntax
    import_method: Annotated[ImportMethod, _IMPORT_METHOD] = ImportMethod.NONE
    feed: Annotated[Feed | None, _FEED] = None

    @model_validator(mode="after")
    def _feed_goes_with_api(self) -> Self:
        if (self.import_method is ImportMethod.API) != (self.feed is not None):
            msg = "feed is required with import_method api and not allowed with none"
            raise ValueError(msg)
        return self


class JobBoardUpdate(BaseModel):
    """Partial update: only the fields sent change. Only `feed` can be null.

    The result must keep `feed` with `api` and only with it: to start importing send both
    fields, to stop send `import_method: none` and `feed: null`.
    """

    name: Text | None = None
    search_url_template: SearchUrlTemplate | None = None
    syntax: Syntax | None = None
    import_method: Annotated[ImportMethod | None, _IMPORT_METHOD] = None
    feed: Annotated[Feed | None, _FEED] = None

    @field_validator("name", "search_url_template", "syntax", "import_method")
    @classmethod
    def _reject_null(cls, value: object) -> object:
        # Runs only for fields sent in the body, so omitting one stays valid.
        if value is None:
            msg = "is required and cannot be cleared"
            raise ValueError(msg)
        return value


class JobBoardRead(BaseModel):
    id: UUID
    name: str
    search_url_template: str
    syntax: Syntax
    import_method: ImportMethod
    feed: Feed | None
    last_imported_at: datetime | None = Field(description="Null if never imported.")
    next_import_at: datetime | None = Field(
        description="Earliest next import (6 hours later); null if never imported."
    )


class GeneratedSearchRead(BaseModel):
    query: str = Field(description="The search, in the job board's syntax.")
    url: str = Field(description="The job board's search URL, ready to open.")


class JobBoardSearchesRead(BaseModel):
    job_board_id: UUID
    job_board_name: str
    syntax: Syntax
    searches: list[GeneratedSearchRead] = Field(
        description="One search, or one per job title for `keywords` job boards."
    )


class ProfileSearchesRead(BaseModel):
    profile_id: UUID
    work_modes: list[WorkMode] = Field(
        description="Not part of the URLs: set them with each job board's own filter."
    )
    job_boards: list[JobBoardSearchesRead] = Field(
        description="Every job board that is not imported, in alphabetical order."
    )


class SearchProfileRead(BaseModel):
    id: UUID
    name: str
    titles: list[str]
    keywords: list[str]
    excluded_keywords: list[str]
    location: str | None
    work_modes: list[WorkMode]
