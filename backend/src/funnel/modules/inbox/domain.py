"""Offer status rules, duplicate detection and what a reading of an offer may keep.

Source of truth: specs/inbox/inbox.feature, specs/inbox/job_board_imports.feature and
specs/inbox/offer_readings.feature.
"""

import html
import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from http import HTTPStatus
from typing import Final
from uuid import UUID

from funnel.core.exceptions import AppError, DomainError
from funnel.modules.discovery.domain import Feed, SearchTerms, WorkMode


class OfferStatus(StrEnum):
    PENDING = "pending"
    DISCARDED = "discarded"
    PROMOTED = "promoted"


class Ats(StrEnum):
    """Applicant tracking systems whose public job boards can be read (no limits stated)."""

    ASHBY = "ashby"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"


class Rule(StrEnum):
    """The rules an imported offer is checked against to fit a search profile."""

    TITLE = "title"
    KEYWORDS = "keywords"
    EXCLUDED = "excluded"
    WORK_MODE = "work_mode"
    LOCATION = "location"
    STABLE = "stable"


class RuleResult(StrEnum):
    PASSED = "passed"
    UNKNOWN = "unknown"  # the offer has not been read, or its reading does not say
    FAILED = "failed"


@dataclass(frozen=True)
class RuleCheck:
    """One rule of a search profile against an offer, with what explains its result."""

    rule: Rule
    result: RuleResult
    found: Sequence[str] = ()
    missing: Sequence[str] = ()
    value: WorkMode | bool | None = None
    evidence: str | None = None


@dataclass(frozen=True)
class FilterReason:
    """Each rule of the reference profile against an offer. Source of truth:
    specs/inbox/filter_reasons.feature."""

    search_profile_id: UUID | None
    search_profile_name: str | None
    has_description: bool
    rules: Sequence[RuleCheck]
    # Marked rightly filtered: reviewed, so no longer worth a second look.
    is_rightly_filtered: bool = False

    @property
    def failed(self) -> list[Rule]:
        return [check.rule for check in self.rules if check.result is RuleResult.FAILED]

    @property
    def near_miss(self) -> bool:
        return is_near_miss(self.failed) and not self.is_rightly_filtered


def is_near_miss(failed: Sequence[Rule]) -> bool:
    """Filtered by a single rule, and not by its title (a title is never unknown)."""
    return len(failed) == 1 and Rule.TITLE not in failed


class Review(StrEnum):
    """What the user did with a filtered offer: promoted it, or left it filtered."""

    RESCUED = "rescued"
    RIGHTLY_FILTERED = "rightly_filtered"


@dataclass(frozen=True)
class ReviewMade:
    """A review and the rules that filtered the offer when it was made."""

    review: Review
    rules: Sequence[Rule]


@dataclass(frozen=True)
class OfferFilter:
    """Which offers to list; None means either."""

    status: OfferStatus | None = None
    is_filtered: bool | None = None
    is_near_miss: bool | None = None
    failed_rule: Rule | None = None


@dataclass(frozen=True)
class FilteredCounts:
    filtered: int
    near_misses: int
    failing: Mapping[Rule, int]
    reviewed_near_misses: int
    rescued_near_misses: int


class DiscardReason(StrEnum):
    """Why an offer was discarded. EXPIRED is only set by the imports."""

    TITLE_WORD = "title_word"
    STACK = "stack"
    LOCATION = "location"
    CONTRACT = "contract"
    COMPANY = "company"
    NONE = "none"
    EXPIRED = "expired"


EXPIRED_REASON: Final = DiscardReason.EXPIRED


def is_title_word(word: str, title: str) -> bool:
    """A whole word of the title, ignoring case: "C++" is one of "Senior C++ Developer"."""
    return re.search(rf"(?<!\w){re.escape(word)}(?!\w)", title, flags=re.IGNORECASE) is not None


# Feeds that publish only their latest offers: one that left them may still be open, so
# their offers are not expired (Jobicy's 100 newest are a few hours of postings).
LATEST_ONLY_FEEDS: Final = frozenset({Feed.JOBICY})


@dataclass(frozen=True)
class FeedOffer:
    """An offer as a feed publishes it; `url` is the link its terms ask to keep."""

    title: str
    company: str
    description: str
    url: str


# Offers read per request: the offer reader's plan allows about this many a minute.
READING_BATCH_SIZE: Final = 5

_TAG: Final = re.compile(r"<[^>]+>")


def plain_text(description: str) -> str:
    """The description as the text a person reads: no tags, entities or extra spaces."""
    return " ".join(html.unescape(_TAG.sub(" ", description)).split())


@dataclass(frozen=True)
class OfferText:
    """What the offer reader is given; `description` is plain text."""

    title: str
    company: str
    description: str


@dataclass(frozen=True)
class Reading:
    """What a description says; None is what it does not say."""

    work_mode: WorkMode | None = None
    work_mode_evidence: str | None = None
    admits_location: bool | None = None
    admits_location_evidence: str | None = None
    stable: bool | None = None
    stable_evidence: str | None = None


def _quoted(evidence: str | None, text: str) -> str | None:
    """The evidence, if the text says it letter for letter (spaces aside)."""
    quote = " ".join((evidence or "").split())
    return quote if quote and quote in text else None


def supported(answer: Reading, text: str, *, asked_location: bool) -> Reading:
    """Only the answers whose evidence is in the text: the reader cannot make one up."""
    work_mode = _quoted(answer.work_mode_evidence, text)
    admits = _quoted(answer.admits_location_evidence, text) if asked_location else None
    stable = _quoted(answer.stable_evidence, text)
    return Reading(
        work_mode=answer.work_mode if work_mode else None,
        work_mode_evidence=work_mode if answer.work_mode is not None else None,
        admits_location=answer.admits_location if admits else None,
        admits_location_evidence=admits if answer.admits_location is not None else None,
        stable=answer.stable if stable else None,
        stable_evidence=stable if answer.stable is not None else None,
    )


@dataclass(frozen=True)
class WordHits:
    """The words of a search profile that appear in an offer, as the database finds them:
    titles and excluded keywords in its title, keywords in its title or description."""

    titles: Sequence[str] = ()
    keywords: Sequence[str] = ()
    excluded: Sequence[str] = ()


@dataclass(frozen=True)
class ProfileMatch:
    """An offer against one search profile: its words and its reading for the profile's
    location, if it was read for it."""

    terms: SearchTerms
    hits: WordHits
    reading: Reading | None = None


def _result(passes: bool | None) -> RuleResult:
    if passes is None:
        return RuleResult.UNKNOWN
    return RuleResult.PASSED if passes else RuleResult.FAILED


def check_rules(match: ProfileMatch) -> list[RuleCheck]:
    """The rules the profile asks for: title and stable always, the others when it has
    some. Only what the reading says can fail a reading rule."""
    terms, hits, reading = match.terms, match.hits, match.reading or Reading()
    checks = [RuleCheck(Rule.TITLE, _result(bool(hits.titles)), found=hits.titles)]
    if terms.keywords:
        missing = [keyword for keyword in terms.keywords if keyword not in hits.keywords]
        checks.append(
            RuleCheck(Rule.KEYWORDS, _result(not missing), found=hits.keywords, missing=missing)
        )
    if terms.excluded_keywords:
        checks.append(RuleCheck(Rule.EXCLUDED, _result(not hits.excluded), found=hits.excluded))
    if terms.work_modes:
        mode = reading.work_mode
        checks.append(
            RuleCheck(
                Rule.WORK_MODE,
                _result(None if mode is None else mode in terms.work_modes),
                value=mode,
                evidence=reading.work_mode_evidence,
            )
        )
    if terms.location is not None:
        admits = reading.admits_location
        checks.append(
            RuleCheck(
                Rule.LOCATION,
                _result(admits),
                value=admits,
                evidence=reading.admits_location_evidence,
            )
        )
    checks.append(
        RuleCheck(
            Rule.STABLE,
            _result(reading.stable),
            value=reading.stable,
            evidence=reading.stable_evidence,
        )
    )
    return checks


def filter_reason(matches: Sequence[ProfileMatch], *, has_description: bool) -> FilterReason:
    """Against the reference profile: the one whose rules the offer fails the fewest times;
    on a tie, the first by name. Without profiles, the title fails."""
    if not matches:
        return FilterReason(None, None, has_description, [RuleCheck(Rule.TITLE, RuleResult.FAILED)])
    checked = [(match.terms, check_rules(match)) for match in matches]
    terms, rules = min(
        checked,
        key=lambda pair: (
            sum(check.result is RuleResult.FAILED for check in pair[1]),
            pair[0].name.casefold(),
        ),
    )
    return FilterReason(terms.search_profile_id, terms.name, has_description, rules)


def count_filtered(
    reasons: Iterable[FilterReason], reviews: Iterable[ReviewMade]
) -> FilteredCounts:
    filtered = [reason for reason in reasons if reason.failed]
    failing = Counter(rule for reason in filtered for rule in reason.failed)
    reviewed = [made.review for made in reviews if is_near_miss(made.rules)]
    return FilteredCounts(
        filtered=len(filtered),
        near_misses=sum(reason.near_miss for reason in filtered),
        failing=dict(failing),
        reviewed_near_misses=len(reviewed),
        rescued_near_misses=reviewed.count(Review.RESCUED),
    )


class OfferReaderError(Exception):
    """The offer reader did not answer for an offer, or answered something unusable."""


class OfferReaderUnavailableError(AppError):
    """No offer reader is configured, so nothing can be read."""

    slug = "offer-reader-unavailable"
    title = "Offer reader not available"
    status = HTTPStatus.SERVICE_UNAVAILABLE


class OfferAction(StrEnum):
    DISCARD = "discard"
    RESTORE = "restore"
    PROMOTE = "promote"


# The only status each action can start from, and the status it leads to.
ACTIONS: Final[Mapping[OfferAction, tuple[OfferStatus, OfferStatus]]] = {
    OfferAction.DISCARD: (OfferStatus.PENDING, OfferStatus.DISCARDED),
    OfferAction.RESTORE: (OfferStatus.DISCARDED, OfferStatus.PENDING),
    OfferAction.PROMOTE: (OfferStatus.PENDING, OfferStatus.PROMOTED),
}


def next_status(current: OfferStatus, action: OfferAction) -> OfferStatus:
    required, result = ACTIONS[action]
    if current is not required:
        raise InvalidOfferStatusError(f"Cannot {action} an offer that is {current}")
    return result


def duplicate_key(company: str, title: str) -> str:
    """Company and title ignoring case and extra spaces: equal keys mean the same offer."""
    return "|".join(" ".join(text.split()).casefold() for text in (company, title))


class InvalidOfferStatusError(DomainError):
    slug = "invalid-offer-status"
    title = "Invalid offer status"
    status = HTTPStatus.CONFLICT


class OfferNotFilteredError(DomainError):
    """Only a filtered offer (pending, imported and fitting no profile) can be reviewed."""

    slug = "offer-not-filtered"
    title = "Offer not filtered"
    status = HTTPStatus.CONFLICT


class WordNotInTitleError(DomainError):
    """A discard because of a word of the title names a word the title does not have."""

    slug = "word-not-in-title"
    title = "Word not in the title"
    status = HTTPStatus.UNPROCESSABLE_CONTENT


class JobBoardNotImportedError(DomainError):
    """Only a job board with an import method can be imported."""

    slug = "job-board-not-imported"
    title = "Job board not imported"
    status = HTTPStatus.CONFLICT


class FeedCooldownError(AppError):
    """The feed was imported too recently: its terms limit how often it may be read."""

    slug = "feed-cooldown"
    title = "Feed imported too recently"
    status = HTTPStatus.TOO_MANY_REQUESTS

    def __init__(self, job_board: str, allowed_at: datetime, now: datetime) -> None:
        wait = int((allowed_at - now).total_seconds())
        super().__init__(
            f"{job_board} can be imported again at {allowed_at.isoformat()}",
            headers={"Retry-After": str(wait)},
        )


class FeedUnavailableError(AppError):
    slug = "feed-unavailable"
    title = "Feed not available"
    status = HTTPStatus.BAD_GATEWAY


class BoardUnavailableError(AppError):
    """The watched company's ATS did not answer, or does not know its board."""

    slug = "board-unavailable"
    title = "Board not available"
    status = HTTPStatus.BAD_GATEWAY


class ImportedByEmailError(DomainError):
    """A job board imported from its email alerts is imported when each alert arrives."""

    slug = "job-board-imported-by-email"
    title = "Job board imported from its email alerts"
    status = HTTPStatus.CONFLICT


class UnsupportedAlertError(AppError):
    """The email does not come from a job alert the app can read."""

    slug = "unsupported-alert"
    title = "Unsupported alert"
    status = HTTPStatus.UNPROCESSABLE_CONTENT


class EmailAlertNotImportedError(DomainError):
    """No job board imports the email alert, so its offers would have no source."""

    slug = "email-alert-not-imported"
    title = "No job board imports this email alert"
    status = HTTPStatus.CONFLICT


class UnknownJobBoardError(AppError):
    """The job board referenced in the request does not exist (422: the path is valid)."""

    slug = "unknown-job-board"
    title = "Unknown job board"
    status = HTTPStatus.UNPROCESSABLE_CONTENT
