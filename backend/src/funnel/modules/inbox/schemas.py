from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, model_validator

from funnel.core.fields import HttpUrlText
from funnel.modules.applications.domain import Channel
from funnel.modules.discovery.domain import WorkMode
from funnel.modules.discovery.schemas import SearchProfileUpdate
from funnel.modules.inbox.domain import (
    Ats,
    DiscardReason,
    OfferStatus,
    Review,
    Rule,
    RuleResult,
)

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class OfferCreate(BaseModel):
    url: Annotated[HttpUrlText, Field(examples=["https://jobs.example/1"])]
    company: Text = Field(description="Company name, as the posting shows it.")
    title: Text = Field(description="Job title; becomes the role when promoted.")
    job_board_id: UUID | None = Field(default=None, description="Where it was found.")
    notes: str | None = None


class DiscardCreate(BaseModel):
    reason: DiscardReason = Field(
        default=DiscardReason.NONE, description="Any but `expired`, which only the imports set."
    )
    word: Text | None = Field(
        default=None,
        description="With `title_word`, and only with it: the word of the title that does not "
        "fit, ignoring case.",
        examples=["Senior"],
    )

    @model_validator(mode="after")
    def _check_reason(self) -> Self:
        if self.reason is DiscardReason.EXPIRED:
            raise ValueError("only the imports discard an offer as expired")
        if (self.reason is DiscardReason.TITLE_WORD) != (self.word is not None):
            raise ValueError("a word goes with the reason title_word, and only with it")
        return self


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


class RuleRead(BaseModel):
    rule: Rule
    result: RuleResult
    found: list[str] = Field(
        description="title: the profile's title in the offer's title; keywords: those found "
        "in the title or the description; excluded: the excluded keyword in the title."
    )
    missing: list[str] = Field(description="keywords: those not found.")
    value: WorkMode | bool | None = Field(
        description="work_mode: the work mode read; location: whether it can be done living "
        "in the profile's location; stable: whether it is a stable job. Null when unknown."
    )
    evidence: str | None = Field(description="The sentence of the description behind `value`.")


class FilterReasonRead(BaseModel):
    search_profile_id: UUID | None = Field(
        description="The reference profile: the one whose rules the offer fails the fewest "
        "times; on a tie, the first by name. Null without search profiles."
    )
    search_profile_name: str | None
    has_description: bool = Field(
        description="Whether there is a description to read: tells an unknown rule apart "
        "from an offer with nothing to read."
    )
    near_miss: bool = Field(description="Filtered, its title passes and it fails exactly one rule.")
    rules: list[RuleRead] = Field(
        description="The rules the reference profile asks for: title and stable always, "
        "the others when the profile has some. The offer is filtered exactly when one fails."
    )


class FilteredCountsRead(BaseModel):
    filtered: int = Field(description="Pending offers that are filtered.")
    near_misses: int = Field(description="Filtered offers that are near misses.")
    failing: dict[Rule, int] = Field(
        description="Filtered offers failing each rule; an offer counts in each it fails."
    )
    reviewed_near_misses: int = Field(
        description="Offers ever reviewed (rescued or marked rightly filtered) while they "
        "were near misses, whatever their status now."
    )
    rescued_near_misses: int = Field(description="Of those, the ones rescued.")


class CriteriaPreviewCreate(SearchProfileUpdate):
    """The changes editing the profile would take, saving nothing. Its name changes nothing."""

    search_profile_id: UUID


class CriteriaPreviewRead(BaseModel):
    entering_pending: int = Field(description="Pending offers filtered now that would not be.")
    leaving_pending: int = Field(description="Pending offers not filtered now that would be.")
    promoted_filtered: int = Field(
        description="Promoted offers that fit the profiles now and would not with the change."
    )
    discarded_filtered: int = Field(
        description="Discarded offers, not expired, that fit the profiles now and would not "
        "with the change."
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
    filtered: bool = Field(
        description="Pending, imported and fitting none of the current search profiles, "
        "by its words or by what its readings say."
    )
    filter_reason: FilterReasonRead | None = Field(
        description="Each rule against the reference profile; only for pending imported offers."
    )
    readings: list[ReadingRead] = Field(
        description="What its description says, once read, for each profile location."
    )
    discard_reason: DiscardReason | None = Field(description="Set while the offer is discarded.")
    discard_word: str | None = Field(description="The word of the title, with `title_word`.")
    application_id: UUID | None = Field(description="Set once the offer is promoted.")
    review: Review | None = Field(
        description="`rescued`: promoted while filtered; `rightly_filtered`: marked so while "
        "filtered, and no longer a near miss."
    )
    review_rules: list[Rule] = Field(description="The rules that filtered it when reviewed.")
    watched_company_id: UUID | None = Field(
        description="The watched company it was imported from, if still watched."
    )
    watched_company_name: str | None
    created_at: datetime
