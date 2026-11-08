from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from funnel.core.fields import HttpUrlText
from funnel.modules.applications.domain import Channel
from funnel.modules.inbox.domain import Feed, OfferStatus

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


class ImportCreate(BaseModel):
    profile_id: UUID = Field(description="The search profile the feed's offers must match.")


class ImportRead(BaseModel):
    feed: Feed
    found: int = Field(description="Offers the feed returned.")
    matching: int = Field(description="Offers that match the profile.")
    added: int = Field(description="Matching offers added to the inbox as pending.")
    already_in_inbox: int = Field(description="Matching offers skipped as duplicates.")
    expired: int = Field(description="Pending offers of this feed discarded as expired.")
    imported_at: datetime


class FeedRead(BaseModel):
    feed: Feed
    last_imported_at: datetime | None
    next_import_at: datetime | None = Field(
        description="Earliest next import (6 hours later); null if never imported."
    )


class OfferRead(BaseModel):
    id: UUID
    url: str
    company: str
    title: str
    job_board_id: UUID | None
    job_board_name: str | None
    notes: str | None
    status: OfferStatus
    discard_reason: str | None = Field(description="Set while the offer is discarded.")
    application_id: UUID | None = Field(description="Set once the offer is promoted.")
    feed: Feed | None = Field(description="The public feed it was imported from, if any.")
    created_at: datetime
