from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from funnel.core.fields import HttpUrlText
from funnel.modules.applications.domain import Channel
from funnel.modules.discovery.domain import WorkMode
from funnel.modules.inbox.domain import Ats, OfferStatus

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
    job_board_id: UUID
    found: int = Field(description="Offers the job board's feed returned.")
    added: int = Field(description="New offers added to the inbox as pending.")
    filtered: int = Field(description="Added offers that fit no search profile.")
    already_in_inbox: int = Field(description="Offers skipped as duplicates.")
    expired: int = Field(
        description="Pending imported offers of this job board discarded as expired."
    )
    imported_at: datetime


class AlertEmailCreate(BaseModel):
    sender: Annotated[str, StringConstraints(strip_whitespace=True, max_length=320)] = Field(
        description="The email address it comes from.", examples=["jobalerts-noreply@linkedin.com"]
    )
    text: Annotated[str, StringConstraints(max_length=1_000_000)] = Field(
        description="The plain-text body of the email."
    )


class AlertImportRead(BaseModel):
    job_board_id: UUID = Field(description="The job board that imports the alert.")
    found: int = Field(description="Offers the alert listed.")
    added: int = Field(description="New offers added to the inbox as pending.")
    filtered: int = Field(description="Added offers that fit no search profile.")
    already_in_inbox: int = Field(description="Offers skipped as duplicates.")
    imported_at: datetime


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


class ReadingRead(BaseModel):
    """What the offer's description says. Null is what it does not say; every answer has
    its evidence, a sentence of the description."""

    location: str | None = Field(
        description="The search profile location it was read for; null for profiles without one."
    )
    work_mode: WorkMode | None
    work_mode_evidence: str | None
    admits_location: bool | None = Field(
        description="Whether the job can be done living in `location`."
    )
    admits_location_evidence: str | None
    stable: bool | None = Field(
        description="Full-time with no end date, as an employee or a contractor (true); "
        "paid by the task or the hour, temporary or part-time (false)."
    )
    stable_evidence: str | None


class ReadingBatchRead(BaseModel):
    read: int = Field(description="Readings made now, one per offer and location.")
    failed: int = Field(description="Readings the offer reader failed on; left to be read.")
    left: int = Field(description="Readings still to be made, the failed ones included.")


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
        description="Pending, imported and fitting none of the current search profiles, "
        "by its words or by what its readings say."
    )
    readings: list[ReadingRead] = Field(
        description="What its description says, once read, for each profile location."
    )
    discard_reason: str | None = Field(description="Set while the offer is discarded.")
    application_id: UUID | None = Field(description="Set once the offer is promoted.")
    watched_company_id: UUID | None = Field(
        description="The watched company it was imported from, if still watched."
    )
    watched_company_name: str | None
    created_at: datetime
