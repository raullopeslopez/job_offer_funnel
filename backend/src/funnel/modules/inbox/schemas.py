from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from funnel.core.fields import HttpUrlText
from funnel.modules.applications.domain import Channel
from funnel.modules.inbox.domain import Ats, Feed, OfferStatus

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class OfferCreate(BaseModel):
    url: Annotated[HttpUrlText, Field(examples=["https://jobs.example/1"])]
    company: Text = Field(description="Company name, as the posting shows it.")
    title: Text = Field(description="Job title; becomes the role when promoted.")
    job_board_id: UUID | None = Field(default=None, description="Where it was found.")
    notes: str | None = None


class DiscardCreate(BaseModel):
    reason: Text | None = Field(default=None, examples=["Not remote"])


class PromotionCreate(BaseModel):
    channel: Channel = Field(default=Channel.PORTAL, description="The application's channel.")


class ImportRead(BaseModel):
    feed: Feed
    found: int = Field(description="Offers the feed returned.")
    added: int = Field(description="New offers added to the inbox as pending.")
    filtered: int = Field(description="Added offers that fit no search profile.")
    already_in_inbox: int = Field(description="Offers skipped as duplicates.")
    expired: int = Field(description="Pending offers of this feed discarded as expired.")
    imported_at: datetime


class FeedRead(BaseModel):
    feed: Feed
    last_imported_at: datetime | None
    next_import_at: datetime | None = Field(
        description="Earliest next import (6 hours later); null if never imported."
    )


class WatchedCompanyCreate(BaseModel):
    name: Text = Field(description="Unique ignoring case; the company of its imported offers.")
    ats: Ats
    board: Text = Field(
        description="The company's name in its public careers URL on the ATS "
        "(boards.greenhouse.io/<board>, jobs.lever.co/<board>, jobs.ashbyhq.com/<board>).",
        examples=["acme"],
    )


class WatchedCompanyRead(BaseModel):
    id: UUID
    name: str
    ats: Ats
    board: str
    created_at: datetime


class BoardImportRead(BaseModel):
    watched_company_id: UUID
    found: int = Field(description="Open offers the company's board returned.")
    added: int = Field(description="New offers added to the inbox as pending.")
    filtered: int = Field(description="Added offers that fit no search profile.")
    already_in_inbox: int = Field(description="Offers skipped as duplicates.")
    expired: int = Field(description="Pending offers of this company discarded as expired.")
    imported_at: datetime


class OfferRead(BaseModel):
    id: UUID
    url: str
    company: str
    title: str
    job_board_id: UUID | None
    job_board_name: str | None
    notes: str | None
    status: OfferStatus
    filtered: bool = Field(
        description="Pending, imported and fitting none of the current search profiles."
    )
    discard_reason: str | None = Field(description="Set while the offer is discarded.")
    application_id: UUID | None = Field(description="Set once the offer is promoted.")
    feed: Feed | None = Field(description="The public feed it was imported from, if any.")
    watched_company_id: UUID | None = Field(
        description="The watched company it was imported from, if still watched."
    )
    watched_company_name: str | None
    created_at: datetime
