from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from funnel.core.fields import HttpUrlText
from funnel.modules.applications.domain import Channel
from funnel.modules.inbox.domain import OfferStatus

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
    created_at: datetime
