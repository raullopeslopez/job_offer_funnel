from datetime import date, datetime
from typing import Annotated, Any, Self
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
    ProfileRule,
    Review,
    Rule,
    RuleResult,
    SuggestionSource,
    Verdict,
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


class TriageBatchRead(BaseModel):
    triaged: int = Field(description="Offers triaged now: each has a verdict.")
    ok: int = Field(description="Of those, the ones marked `ok`.")
    ko: int = Field(description="Of those, the ones marked `ko`: false positives.")
    to_rescue: int = Field(
        description="Near misses triaged now and marked `ok`: false negatives, worth rescuing."
    )
    failed: int = Field(description="Offers the triager did not answer for; left to triage.")
    left: int = Field(description="Offers still to triage, the failed ones included.")


class TriagerRead(BaseModel):
    is_available: bool = Field(description="Whether an offer triager is configured.")


class TriageRead(BaseModel):
    """What the offer triager says of an offer; it is never applied on its own."""

    verdict: Verdict = Field(
        description="`ok`: worth the user's time; `ko`: a false positive, it passed the "
        "filters but the user would discard it."
    )
    why: str = Field(description="One sentence in the triager's words, up to 200 characters.")


class SuggestedDiscardRead(BaseModel):
    """A discard the offer triager suggests; it is never applied on its own."""

    reason: DiscardReason = Field(description="title_word, stack, location, contract or company.")
    evidence: str = Field(
        description="With `title_word`, the word of the title (the discard's word); otherwise "
        "a sentence of the description."
    )


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


class CriteriaChangeCreate(CriteriaPreviewCreate):
    """One rule of the profile, with its new value; the name cannot be changed here."""

    offer_id: UUID | None = Field(default=None, description="The offer it came from.")

    @model_validator(mode="after")
    def _check_one_rule(self) -> Self:
        if len(self.rules()) != 1 or "name" in self.model_fields_set:
            raise ValueError(f"exactly one of {', '.join(ProfileRule)} changes")
        return self

    def rules(self) -> dict[ProfileRule, Any]:
        """The rule sent, with its value as JSON."""
        sent = self.model_dump(
            mode="json", include={str(rule) for rule in ProfileRule}, exclude_unset=True
        )
        return {ProfileRule(rule): value for rule, value in sent.items()}


# The value of a rule: a list of words or modes, or the location.
RuleValue = list[str] | str | None


class CriteriaChangeRead(BaseModel):
    id: UUID
    search_profile_id: UUID
    search_profile_name: str
    offer_id: UUID | None
    rule: ProfileRule
    before: RuleValue
    after: RuleValue
    entering_pending: int = Field(description="Pending offers it brought in when applied.")
    leaving_pending: int = Field(description="Pending offers it took out when applied.")
    promoted_filtered: int = Field(description="Promoted offers it would have filtered.")
    discarded_filtered: int = Field(description="Discarded offers it would have filtered.")
    created_at: datetime


class CriteriaSuggestionRead(BaseModel):
    search_profile_id: UUID
    search_profile_name: str
    source: SuggestionSource = Field(
        description="`count`: counted from the decisions; `triager`: suggested by the offer "
        "triager, with why."
    )
    why: str | None = Field(description="The triager's why; null for a counted suggestion.")
    rule: ProfileRule = Field(
        description="The rule it changes: `excluded_keywords` (exclude a word, or stop "
        "excluding it), `keywords` (stop asking for one) or `work_modes` (accept one)."
    )
    word: str = Field(description="The word or work mode it adds or takes out.")
    after: RuleValue = Field(description="The rule's value with the change: the change to make.")
    offer_ids: list[UUID] = Field(
        description="Counted: the discarded offers with the word. From the triager: the "
        "offers it comes from (`ko` offers, or an `ok` near miss to relax its rule); accepting "
        "it from one is a criteria change with its `offer_id`."
    )
    discarded: int = Field(description="All the discarded offers, expired ones left out.")
    preview: CriteriaPreviewRead = Field(description="What excluding the word would do.")


class DismissalCreate(BaseModel):
    search_profile_id: UUID
    rule: ProfileRule = Field(
        default=ProfileRule.EXCLUDED_KEYWORDS, description="The rule of the suggestion."
    )
    word: Text


class DismissalRead(BaseModel):
    search_profile_id: UUID
    rule: ProfileRule
    word: str


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
    discarded_fitting: int = Field(
        description="Discarded offers, not expired, that do not fit the profiles now and "
        "would with the change."
    )


class QualityFiguresRead(BaseModel):
    decided: int = Field(
        description="Offers decided from Pending: promoted or discarded, without rescues "
        "and expired ones."
    )
    promoted_from_pending: int
    precision: float | None = Field(description="promoted_from_pending ÷ decided, in %.")
    reviewed_near_misses: int = Field(description="Near misses rescued or rightly filtered.")
    rescued_near_misses: int
    losses: float | None = Field(description="rescued ÷ reviewed near misses, in %.")
    fitting: int = Field(description="Imported offers that fit the profiles as they are now.")
    promoted: int = Field(description="Promoted offers, rescues included.")
    applied: int = Field(description="Of the promoted, applications that reached `applied`.")
    answered: int = Field(description="Of the promoted, applications that reached `screening`.")
    suggested_decided: int = Field(
        description="Triaged offers with a suggested discard that were promoted or discarded."
    )
    suggested_discarded: int = Field(description="Of those, the ones discarded.")
    triager_precision: float | None = Field(
        description="suggested_discarded ÷ suggested_decided, in %."
    )
    triaged_discarded: int = Field(description="Triaged offers discarded, expired ones left out.")
    missed_discards: int = Field(description="Of those, the ones marked `ok`.")
    triager_misses: float | None = Field(description="missed_discards ÷ triaged_discarded, in %.")
    ok_near_misses_reviewed: int = Field(
        description="Near misses the triager marked `ok` that were rescued or rightly filtered."
    )
    ok_near_misses_rescued: int = Field(description="Of those, the ones rescued.")
    triager_rescues: float | None = Field(
        description="ok_near_misses_rescued ÷ ok_near_misses_reviewed, in %."
    )
    triaged_near_misses_rescued: int = Field(description="Near misses triaged and rescued.")
    lost_rescues: int = Field(description="Of those, the ones the triager marked `ko`.")
    triager_lost_rescues: float | None = Field(
        description="lost_rescues ÷ triaged_near_misses_rescued, in %."
    )


class WeekQualityRead(QualityFiguresRead):
    starts_on: date


class DiscardReasonCountRead(BaseModel):
    reason: DiscardReason
    offers: int


class SourceQualityRead(BaseModel):
    source: str = Field(description="The job board or watched company the offers came from.")
    imported: int
    fitting: int
    promoted: int
    discarded: int = Field(description="Discarded by the user: expired ones are left out.")


class OfferQualityRead(BaseModel):
    starts_on: date = Field(description="First day of the 4 weeks, which end today.")
    total: QualityFiguresRead
    weeks: list[WeekQualityRead] = Field(description="The 4 weeks, the oldest first.")
    fitting_per_week: float = Field(description="Fitting offers a week, on average.")
    near_misses_left: int = Field(description="Pending near misses not reviewed yet.")
    discard_reasons: list[DiscardReasonCountRead] = Field(
        description="Discards by reason, the most frequent first; expired ones left out."
    )
    sources: list[SourceQualityRead]


class FrequentTitleRead(BaseModel):
    title: str = Field(description="As most often written.")
    offers: int
    with_keywords: int = Field(description="Offers with all the profile's keywords.")
    reading_passes: int = Field(
        description="Offers whose reading does not rule out the profile's work mode, "
        "location or contract."
    )
    titles: list[str] = Field(description="The profile's titles with this one: the change.")
    preview: CriteriaPreviewRead = Field(description="What adding the title would do.")


class FrequentTitlesRead(BaseModel):
    offers: int = Field(description="Filtered offers with none of the profile's titles.")
    titles: list[FrequentTitleRead] = Field(
        description="Titles of at least 2 of them, the most frequent first (up to 5)."
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
    triage: TriageRead | None = Field(description="The triager's verdict; null until triaged.")
    suggested_discard: SuggestedDiscardRead | None = Field(
        description="With a `ko` verdict whose evidence holds, the discard it suggests; null "
        "otherwise."
    )
    watched_company_id: UUID | None = Field(
        description="The watched company it was imported from, if still watched."
    )
    watched_company_name: str | None
    created_at: datetime
