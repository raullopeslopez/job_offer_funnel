"""Offer status rules, duplicate detection and what a reading of an offer may keep.

Source of truth: specs/inbox/inbox.feature, specs/inbox/job_board_imports.feature,
specs/inbox/offer_readings.feature and specs/inbox/offer_countries.feature.
"""

import html
import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from http import HTTPStatus
from typing import Final
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID

from funnel.core.exceptions import AppError, DomainError
from funnel.modules.applications.domain import Stage
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


class Verdict(StrEnum):
    """What the offer triager says of an offer: worth the user's time (ok) or not (ko)."""

    OK = "ok"
    KO = "ko"


class Confidence(StrEnum):
    """How sure the offer triager is of its verdict."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class Why:
    """One side of a triage: a sentence in the triager's words, and the text of the offer
    that backs it, if it is in the offer."""

    why: str
    quote: str | None = None


@dataclass(frozen=True)
class Triage:
    """The triager's verdict on an offer: what speaks for it and against it, and how sure
    it is."""

    verdict: Verdict
    why_yes: Why | None = None
    why_not: Why | None = None
    confidence: Confidence | None = None


class SuggestionSource(StrEnum):
    """Where a criteria suggestion comes from: counted from the decisions, or the triager."""

    COUNT = "count"
    TRIAGER = "triager"


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
    """Which offers to list, None meaning either, and whether by verdict instead of only from
    the most recently added, and with the variants of each offer one after another."""

    status: OfferStatus | None = None
    is_filtered: bool | None = None
    is_near_miss: bool | None = None
    failed_rule: Rule | None = None
    matching_company_or_title: str | None = None
    job_board_id: UUID | None = None
    is_by_verdict: bool = False
    has_variants_together: bool = False


@dataclass(frozen=True)
class FilteredCounts:
    filtered: int
    near_misses: int
    failing: Mapping[Rule, int]
    reviewed_near_misses: int
    rescued_near_misses: int


@dataclass(frozen=True)
class FitChange:
    """How many imported offers in a status fit the profiles now and with a change."""

    status: OfferStatus
    fits_now: bool
    fits_after: bool
    offers: int


@dataclass(frozen=True)
class CriteriaPreview:
    """What a change to a profile would do. Source of truth:
    specs/inbox/criteria_previews.feature."""

    entering_pending: int
    leaving_pending: int
    promoted_filtered: int
    discarded_filtered: int
    discarded_fitting: int


def preview_criteria(changes: Iterable[FitChange]) -> CriteriaPreview:
    counts: Counter[tuple[OfferStatus, bool]] = Counter()
    for change in changes:
        if change.fits_now != change.fits_after:
            counts[change.status, change.fits_after] += change.offers
    return CriteriaPreview(
        entering_pending=counts[OfferStatus.PENDING, True],
        leaving_pending=counts[OfferStatus.PENDING, False],
        promoted_filtered=counts[OfferStatus.PROMOTED, False],
        discarded_filtered=counts[OfferStatus.DISCARDED, False],
        discarded_fitting=counts[OfferStatus.DISCARDED, True],
    )


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


# --- Criteria suggestions (specs/inbox/criteria_suggestions.feature) ---

SUGGESTION_MIN_DISCARDS: Final = 3
_TITLE_WORD: Final = re.compile(r"\w[\w+#]*")


@dataclass(frozen=True)
class WordInDiscards:
    """A word of the titles (as first seen) and the discarded offers that have it."""

    word: str
    offer_ids: Sequence[UUID]


def exclusion_candidates(
    discarded: Sequence[tuple[UUID, str]], promoted_titles: Sequence[str]
) -> list[WordInDiscards]:
    """Words in enough discarded titles and in no promoted one, the most frequent first."""
    in_promoted = {
        word.casefold() for title in promoted_titles for word in _TITLE_WORD.findall(title)
    }
    seen: dict[str, str] = {}
    offers: dict[str, list[UUID]] = {}
    for offer_id, title in discarded:
        for word in dict.fromkeys(word.casefold() for word in _TITLE_WORD.findall(title)):
            offers.setdefault(word, []).append(offer_id)
        for word in _TITLE_WORD.findall(title):
            seen.setdefault(word.casefold(), word)
    candidates = [
        WordInDiscards(seen[word], ids)
        for word, ids in offers.items()
        if len(ids) >= SUGGESTION_MIN_DISCARDS and word not in in_promoted
    ]
    return sorted(candidates, key=lambda c: (-len(c.offer_ids), c.word.casefold()))


def can_exclude(word: str, terms: SearchTerms) -> bool:
    """Not excluded by the profile yet, and not part of what the profile looks for."""
    excluded = {keyword.casefold() for keyword in terms.excluded_keywords}
    wanted = [*terms.titles, *terms.keywords]
    return word.casefold() not in excluded and not any(
        is_title_word(word, phrase) for phrase in wanted
    )


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
    # Where the job is, as the source publishes it; None when it publishes none.
    location: str | None = None


# Offers read per request: the offer reader's plan allows about this many a minute.
READING_BATCH_SIZE: Final = 5

_TAG: Final = re.compile(r"<[^>]+>")


def plain_text(description: str) -> str:
    """The description as the text a person reads: no tags, entities or extra spaces."""
    return " ".join(html.unescape(_TAG.sub(" ", description)).split())


@dataclass(frozen=True)
class OfferText:
    """What the offer reader and the triager are given; `description` is plain text and
    `location` the one its source publishes. A near miss also says the rule that filtered
    it."""

    title: str
    company: str
    description: str
    filtered_by: RuleCheck | None = None
    location: str | None = None

    @property
    def evidence(self) -> str:
        """Where an answer's evidence may be: the title, the location and the description,
        one per line so that no quote spans two of them."""
        parts = (self.title, self.location or "", self.description)
        return "\n".join(" ".join(part.split()) for part in parts)


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
    """The evidence, if one line of the text says it letter for letter (spaces aside)."""
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


# --- Offer triages (specs/inbox/offer_triages.feature) ---

# What the triager is told (how many offers per request is each triager's: triager.py).
TRIAGE_DECISIONS: Final = 30
TRIAGE_MISTAKES: Final = 20
SUGGESTED_REASONS: Final = frozenset(
    {
        DiscardReason.TITLE_WORD,
        DiscardReason.STACK,
        DiscardReason.LOCATION,
        DiscardReason.CONTRACT,
        DiscardReason.COMPANY,
    }
)


@dataclass(frozen=True)
class SuggestedDiscard:
    """A discard the triager suggests: for title_word the evidence is the word."""

    reason: DiscardReason
    evidence: str


@dataclass(frozen=True)
class TriageAnswer:
    """What the triager says of an offer, not trusted yet: its verdict, why yes and why not
    with their quotes, its confidence and, for a KO, a discard reason and its evidence."""

    verdict: str | None = None
    why_yes: str | None = None
    why_not: str | None = None
    reason: str | None = None
    evidence: str | None = None
    quote_yes: str | None = None
    quote_not: str | None = None
    confidence: str | None = None


@dataclass(frozen=True)
class TriagerSuggestion:
    """A word the triager suggests excluding from a profile (by its name), with why and the
    offers of the batch it comes from (by their position); not trusted yet."""

    profile: str
    word: str
    why: str
    offers: Sequence[int]


@dataclass(frozen=True)
class TriageReply:
    """What the triager answers for a batch: by offer position (an offer it did not answer
    for is missing), and the exclusions it suggests."""

    answers: Mapping[int, TriageAnswer]
    suggestions: Sequence[TriagerSuggestion] = ()


class Mistake(StrEnum):
    REJECTED_SUGGESTION = "rejected_suggestion"
    MISSED_DISCARD = "missed_discard"


@dataclass(frozen=True)
class Decision:
    """An offer I promoted (no reason) or discarded, as the triager is told it."""

    title: str
    status: OfferStatus
    reason: DiscardReason | None = None
    word: str | None = None


@dataclass(frozen=True)
class TriageMistake:
    title: str
    mistake: Mistake
    reason: DiscardReason | None = None


@dataclass(frozen=True)
class TriageContext:
    """What the triager is told once per request, with the offers."""

    profiles: Sequence[SearchTerms]
    decisions: Sequence[Decision]
    mistakes: Sequence[TriageMistake]


WHY_LENGTH: Final = 200


def _why(why: str | None, quote: str | None, offer: OfferText) -> Why | None:
    """One side, cut to 200 characters, with its quote only if the offer says it; none when
    there is nothing to say."""
    sentence = " ".join((why or "").split())[:WHY_LENGTH]
    if not sentence:
        return None
    return Why(sentence, _quoted(quote, offer.title) or _quoted(quote, offer.description))


def kept_triage(answer: TriageAnswer, offer: OfferText) -> Triage | None:
    """The verdict, why yes and why not and the confidence, if the verdict is OK or KO; a
    confidence that is not low, medium or high is left out. None is no answer: the offer is
    left to be triaged again."""
    verdict = next((v for v in Verdict if v == (answer.verdict or "").lower()), None)
    if verdict is None:
        return None
    return Triage(
        verdict,
        _why(answer.why_yes, answer.quote_yes, offer),
        _why(answer.why_not, answer.quote_not, offer),
        next((c for c in Confidence if c == (answer.confidence or "").lower()), None),
    )


def kept_suggestion(answer: TriageAnswer, offer: OfferText) -> SuggestedDiscard | None:
    """The suggested discard of a KO, if its reason is of the list and its evidence holds: a
    word of the title for title_word, a sentence of the description for the others."""
    reason = next((r for r in SUGGESTED_REASONS if r == answer.reason), None)
    if reason is None or (answer.verdict or "").lower() != Verdict.KO:
        return None
    if reason is DiscardReason.TITLE_WORD:
        word = (answer.evidence or "").strip()
        return SuggestedDiscard(reason, word) if word and is_title_word(word, offer.title) else None
    quote = _quoted(answer.evidence, offer.description)
    return None if quote is None else SuggestedDiscard(reason, quote)


# --- Suggested criteria changes of the triager (specs/inbox/offer_triages.feature and
# specs/inbox/near_miss_triages.feature) ---


def _has(words: Iterable[str], word: str) -> bool:
    return word.casefold() in {w.casefold() for w in words}


def _values(terms: SearchTerms, rule: ProfileRule) -> list[str]:
    return [str(value) for value in getattr(terms, rule)]


def rule_after(terms: SearchTerms, rule: ProfileRule, word: str) -> list[str]:
    """The rule's value with the change: the word comes out if the rule has it (an excluded
    word or a keyword); otherwise it goes in (a word to exclude, or a work mode)."""
    current = _values(terms, rule)
    if _has(current, word):
        return [w for w in current if w.casefold() != word.casefold()]
    return [*current, word]


def is_relaxing(terms: SearchTerms, rule: ProfileRule, word: str) -> bool:
    """Whether the change lets more offers in: all but excluding a new word."""
    return rule is not ProfileRule.EXCLUDED_KEYWORDS or _has(terms.excluded_keywords, word)


def can_change(terms: SearchTerms, rule: ProfileRule, word: str) -> bool:
    """Exclude a word the profile does not look for, or stop excluding one; stop asking for
    a keyword it asks for; accept a work mode it does not accept yet."""
    has = _has(_values(terms, rule), word)
    if rule is ProfileRule.EXCLUDED_KEYWORDS:
        return has or can_exclude(word, terms)
    return has if rule is ProfileRule.KEYWORDS else not has


def holds_the_rule(preview: CriteriaPreview, *, relaxing: bool) -> bool:
    """Tightening: it would filter no promoted offer and at least one discarded. Relaxing:
    it would make no discarded offer fit, and bring at least one into Pending."""
    if relaxing:
        return preview.discarded_fitting == 0 and preview.entering_pending > 0
    return preview.promoted_filtered == 0 and preview.discarded_filtered > 0


@dataclass(frozen=True)
class Relaxing:
    """Relaxing the rule that filtered a near miss: the word or work mode it changes."""

    rule: ProfileRule
    word: str


def relaxing(check: RuleCheck) -> Relaxing | None:
    """Stop excluding the word that filtered it, stop asking for the keyword it lacks, or
    accept its work mode. Location and stable are not relaxed."""
    if check.rule is Rule.EXCLUDED and check.found:
        return Relaxing(ProfileRule.EXCLUDED_KEYWORDS, check.found[0])
    if check.rule is Rule.KEYWORDS and check.missing:
        return Relaxing(ProfileRule.KEYWORDS, check.missing[0])
    if check.rule is Rule.WORK_MODE and isinstance(check.value, WorkMode):
        return Relaxing(ProfileRule.WORK_MODES, check.value)
    return None


class OfferTriagerError(Exception):
    """The offer triager did not answer, or answered something unusable."""


class OfferTriagerUnavailableError(AppError):
    """No offer triager is configured, so nothing can be triaged."""

    slug = "offer-triager-unavailable"
    title = "Offer triager not available"
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


# Where a title stops being the role and starts naming a team, a place or a detail: an
# opening parenthesis or bracket, a comma, or a dash or vertical bar set off by a space.
_AFTER_BASE_TITLE: Final = re.compile(r"[(\[,]|\s[-–—|]|[-–—|]\s")


def base_title(title: str) -> str:
    """The title up to its first parenthesis, bracket, comma, or dash or vertical bar set
    off by a space; the whole title when that leaves nothing. A hyphen inside a word
    ("Full-Stack") is part of the word."""
    whole = " ".join(title.split())
    cut = _AFTER_BASE_TITLE.search(whole)
    return (whole[: cut.start()].strip() if cut else whole) or whole


def variant_key(company: str, title: str) -> str:
    """Company and base title ignoring case and extra spaces: equal keys mean variants of
    the same role."""
    return duplicate_key(company, base_title(title))


def url_key(url: str) -> str:
    """The URL without a trailing slash or utm_* parameters: equal keys mean the same offer,
    even if the company edited its title."""
    parts = urlsplit(url)
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.startswith("utm_")
    ]
    return urlunsplit(parts._replace(path=parts.path.rstrip("/"), query=urlencode(query)))


class InvalidOfferStatusError(DomainError):
    slug = "invalid-offer-status"
    title = "Invalid offer status"
    status = HTTPStatus.CONFLICT


class ProfileRule(StrEnum):
    """The rules of a search profile a criteria change edits, one at a time. Source of
    truth: specs/inbox/criteria_changes.feature."""

    TITLES = "titles"
    KEYWORDS = "keywords"
    EXCLUDED_KEYWORDS = "excluded_keywords"
    LOCATION = "location"
    WORK_MODES = "work_modes"


class RuleChangedSinceError(DomainError):
    """A later change edited the same rule: undoing this one would undo that one too."""

    slug = "rule-changed-since"
    title = "Rule changed since"
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


# --- Frequent titles (specs/inbox/frequent_titles.feature) ---

FREQUENT_TITLE_MIN_OFFERS: Final = 2
FREQUENT_TITLES_SHOWN: Final = 5


@dataclass(frozen=True)
class UntitledOffer:
    """A filtered offer with none of a profile's titles, as the frequent titles read it."""

    title: str
    has_keywords: bool
    reading_passes: bool


@dataclass(frozen=True)
class FrequentTitle:
    title: str
    offers: int
    with_keywords: int
    reading_passes: int


def _title_key(title: str) -> str:
    return " ".join(title.split()).casefold()


def frequent_titles(offers: Sequence[UntitledOffer]) -> list[FrequentTitle]:
    """The titles of at least 2 offers, the most frequent first, as most often written."""
    groups: dict[str, list[UntitledOffer]] = {}
    for offer in offers:
        groups.setdefault(_title_key(offer.title), []).append(offer)
    found = [
        FrequentTitle(
            # Counter keeps the first seen first on a tie: the oldest offer's writing.
            title=Counter(offer.title for offer in group).most_common(1)[0][0],
            offers=len(group),
            with_keywords=sum(offer.has_keywords for offer in group),
            reading_passes=sum(offer.reading_passes for offer in group),
        )
        for group in groups.values()
        if len(group) >= FREQUENT_TITLE_MIN_OFFERS
    ]
    found.sort(key=lambda title: (-title.offers, _title_key(title.title)))
    return found[:FREQUENT_TITLES_SHOWN]


# --- Offer quality (specs/inbox/offer_quality.feature) ---

QUALITY_WEEKS: Final = 4
_WEEK_DAYS: Final = 7
_ONE_DECIMAL: Final = Decimal("0.1")


@dataclass(frozen=True)
class QualityOffer:
    """An offer as the quality reads it. `stage` is its application's, if promoted."""

    added_on: date
    status: OfferStatus
    is_imported: bool
    fits: bool
    source: str | None = None
    discard_reason: DiscardReason | None = None
    review: Review | None = None
    review_rules: Sequence[Rule] = ()
    stage: Stage | None = None
    verdict: Verdict | None = None
    suggested_discard: DiscardReason | None = None

    @property
    def is_triaged(self) -> bool:
        return self.verdict is not None

    @property
    def is_decided_from_pending(self) -> bool:
        return self.review is not Review.RESCUED and (
            self.status is OfferStatus.PROMOTED
            or (self.status is OfferStatus.DISCARDED and self.discard_reason is not EXPIRED_REASON)
        )

    @property
    def is_reviewed_near_miss(self) -> bool:
        return self.review is not None and is_near_miss(self.review_rules)

    @property
    def is_discarded(self) -> bool:
        return self.status is OfferStatus.DISCARDED and self.discard_reason is not EXPIRED_REASON


@dataclass(frozen=True)
class QualityFigures:
    """The figures of a set of offers: all 4 weeks, or one of them."""

    decided: int
    promoted_from_pending: int
    precision: float | None
    reviewed_near_misses: int
    rescued_near_misses: int
    losses: float | None
    fitting: int
    promoted: int
    applied: int
    answered: int
    suggested_decided: int
    suggested_discarded: int
    triager_precision: float | None
    triaged_discarded: int
    missed_discards: int
    triager_misses: float | None
    ok_near_misses_reviewed: int
    ok_near_misses_rescued: int
    triager_rescues: float | None
    triaged_near_misses_rescued: int
    lost_rescues: int
    triager_lost_rescues: float | None


@dataclass(frozen=True)
class SourceQuality:
    source: str
    imported: int
    fitting: int
    promoted: int
    discarded: int


@dataclass(frozen=True)
class OfferQuality:
    starts_on: date
    total: QualityFigures
    weeks: Sequence[tuple[date, QualityFigures]]
    fitting_per_week: float
    near_misses_left: int
    discard_reasons: Sequence[tuple[DiscardReason, int]]
    sources: Sequence[SourceQuality]


def rate(part: int, whole: int) -> float | None:
    """A percentage with one decimal, rounding half up; None with nothing to divide by."""
    if whole == 0:
        return None
    return float((Decimal(part) * 100 / Decimal(whole)).quantize(_ONE_DECIMAL, ROUND_HALF_UP))


def quality_starts_on(today: date) -> date:
    return today - timedelta(days=QUALITY_WEEKS * _WEEK_DAYS - 1)


def _figures(offers: Sequence[QualityOffer]) -> QualityFigures:
    decided = [offer for offer in offers if offer.is_decided_from_pending]
    promoted_from_pending = sum(offer.status is OfferStatus.PROMOTED for offer in decided)
    reviewed = [offer for offer in offers if offer.is_reviewed_near_miss]
    rescued = sum(offer.review is Review.RESCUED for offer in reviewed)
    promoted = [offer for offer in offers if offer.status is OfferStatus.PROMOTED]
    stages = list(Stage)
    reached = [stages.index(offer.stage) for offer in promoted if offer.stage is not None]
    triaged = [offer for offer in offers if offer.is_triaged]
    suggested = [
        offer
        for offer in triaged
        if offer.suggested_discard is not None
        and (offer.status is OfferStatus.PROMOTED or offer.is_discarded)
    ]
    suggested_discarded = sum(offer.is_discarded for offer in suggested)
    triaged_discarded = [offer for offer in triaged if offer.is_discarded]
    missed = sum(offer.verdict is Verdict.OK for offer in triaged_discarded)
    # The near misses: OK is worth rescuing, KO rightly filtered.
    ok_reviewed = [o for o in reviewed if o.verdict is Verdict.OK]
    ok_rescued = sum(o.review is Review.RESCUED for o in ok_reviewed)
    triaged_rescued = [o for o in reviewed if o.is_triaged and o.review is Review.RESCUED]
    lost = sum(o.verdict is Verdict.KO for o in triaged_rescued)
    return QualityFigures(
        decided=len(decided),
        promoted_from_pending=promoted_from_pending,
        precision=rate(promoted_from_pending, len(decided)),
        reviewed_near_misses=len(reviewed),
        rescued_near_misses=rescued,
        losses=rate(rescued, len(reviewed)),
        fitting=sum(offer.is_imported and offer.fits for offer in offers),
        promoted=len(promoted),
        applied=sum(index >= stages.index(Stage.APPLIED) for index in reached),
        answered=sum(index >= stages.index(Stage.SCREENING) for index in reached),
        suggested_decided=len(suggested),
        suggested_discarded=suggested_discarded,
        triager_precision=rate(suggested_discarded, len(suggested)),
        triaged_discarded=len(triaged_discarded),
        missed_discards=missed,
        triager_misses=rate(missed, len(triaged_discarded)),
        ok_near_misses_reviewed=len(ok_reviewed),
        ok_near_misses_rescued=ok_rescued,
        triager_rescues=rate(ok_rescued, len(ok_reviewed)),
        triaged_near_misses_rescued=len(triaged_rescued),
        lost_rescues=lost,
        triager_lost_rescues=rate(lost, len(triaged_rescued)),
    )


def _sources(offers: Sequence[QualityOffer]) -> list[SourceQuality]:
    by_source: dict[str, list[QualityOffer]] = {}
    for offer in offers:
        if offer.is_imported and offer.source is not None:
            by_source.setdefault(offer.source, []).append(offer)
    return [
        SourceQuality(
            source=source,
            imported=len(found),
            fitting=sum(offer.fits for offer in found),
            promoted=sum(offer.status is OfferStatus.PROMOTED for offer in found),
            discarded=sum(offer.is_discarded for offer in found),
        )
        for source, found in sorted(by_source.items(), key=lambda item: item[0].casefold())
    ]


def offer_quality(
    offers: Iterable[QualityOffer], today: date, near_misses_left: int
) -> OfferQuality:
    """The quality of the offers added in the 4 weeks up to today, and week by week."""
    starts_on = quality_starts_on(today)
    window = [offer for offer in offers if starts_on <= offer.added_on <= today]
    week_starts = [starts_on + timedelta(days=_WEEK_DAYS * week) for week in range(QUALITY_WEEKS)]
    weeks = [
        (
            start,
            _figures(
                [o for o in window if start <= o.added_on < start + timedelta(days=_WEEK_DAYS)]
            ),
        )
        for start in week_starts
    ]
    total = _figures(window)
    reasons = Counter(
        offer.discard_reason
        for offer in window
        if offer.is_discarded and offer.discard_reason is not None
    )
    per_week = (Decimal(total.fitting) / QUALITY_WEEKS).quantize(_ONE_DECIMAL, ROUND_HALF_UP)
    return OfferQuality(
        starts_on=starts_on,
        total=total,
        weeks=weeks,
        fitting_per_week=float(per_week),
        near_misses_left=near_misses_left,
        discard_reasons=sorted(reasons.items(), key=lambda item: (-item[1], item[0])),
        sources=_sources(window),
    )


# --- Countries of an offer (specs/inbox/offer_countries.feature) ---

# Offers are stored in VARCHAR(200) columns.
_MAX_LOCATION: Final = 200


def published_location(value: object) -> str | None:
    """The location as a source publishes it: a text, or a list of them (Himalayas).
    None when it publishes none, or only blanks."""
    parts = value if isinstance(value, list) else [value]
    texts = [part.strip() for part in parts if isinstance(part, str) and part.strip()]
    return ", ".join(texts)[:_MAX_LOCATION] or None


WORLDWIDE: Final = "Worldwide"
# The English short names of the countries: matched as whole words, ignoring case.
_COUNTRY_NAMES: Final = (
    "Afghanistan",
    "Albania",
    "Algeria",
    "Andorra",
    "Angola",
    "Antigua and Barbuda",
    "Argentina",
    "Armenia",
    "Australia",
    "Austria",
    "Azerbaijan",
    "Bahamas",
    "Bahrain",
    "Bangladesh",
    "Barbados",
    "Belarus",
    "Belgium",
    "Belize",
    "Benin",
    "Bhutan",
    "Bolivia",
    "Bosnia and Herzegovina",
    "Botswana",
    "Brazil",
    "Brunei",
    "Bulgaria",
    "Burkina Faso",
    "Burundi",
    "Cambodia",
    "Cameroon",
    "Canada",
    "Cape Verde",
    "Central African Republic",
    "Chad",
    "Chile",
    "China",
    "Colombia",
    "Comoros",
    "Congo",
    "Costa Rica",
    "Croatia",
    "Cuba",
    "Cyprus",
    "Czech Republic",
    "Czechia",
    "Denmark",
    "Djibouti",
    "Dominica",
    "Dominican Republic",
    "Ecuador",
    "Egypt",
    "El Salvador",
    "Equatorial Guinea",
    "Eritrea",
    "Estonia",
    "Eswatini",
    "Ethiopia",
    "Fiji",
    "Finland",
    "France",
    "Gabon",
    "Gambia",
    "Georgia",
    "Germany",
    "Ghana",
    "Greece",
    "Grenada",
    "Guatemala",
    "Guinea",
    "Guinea-Bissau",
    "Guyana",
    "Haiti",
    "Honduras",
    "Hong Kong",
    "Hungary",
    "Iceland",
    "India",
    "Indonesia",
    "Iran",
    "Iraq",
    "Ireland",
    "Israel",
    "Italy",
    "Ivory Coast",
    "Jamaica",
    "Japan",
    "Jordan",
    "Kazakhstan",
    "Kenya",
    "Kiribati",
    "Kosovo",
    "Kuwait",
    "Kyrgyzstan",
    "Laos",
    "Latvia",
    "Lebanon",
    "Lesotho",
    "Liberia",
    "Libya",
    "Liechtenstein",
    "Lithuania",
    "Luxembourg",
    "Madagascar",
    "Malawi",
    "Malaysia",
    "Maldives",
    "Mali",
    "Malta",
    "Marshall Islands",
    "Mauritania",
    "Mauritius",
    "Mexico",
    "Micronesia",
    "Moldova",
    "Monaco",
    "Mongolia",
    "Montenegro",
    "Morocco",
    "Mozambique",
    "Myanmar",
    "Namibia",
    "Nauru",
    "Nepal",
    "Netherlands",
    "New Zealand",
    "Nicaragua",
    "Niger",
    "Nigeria",
    "North Korea",
    "North Macedonia",
    "Norway",
    "Oman",
    "Pakistan",
    "Palau",
    "Palestine",
    "Panama",
    "Papua New Guinea",
    "Paraguay",
    "Peru",
    "Philippines",
    "Poland",
    "Portugal",
    "Puerto Rico",
    "Qatar",
    "Romania",
    "Russia",
    "Rwanda",
    "Saint Kitts and Nevis",
    "Saint Lucia",
    "Saint Vincent and the Grenadines",
    "Samoa",
    "San Marino",
    "Sao Tome and Principe",
    "Saudi Arabia",
    "Senegal",
    "Serbia",
    "Seychelles",
    "Sierra Leone",
    "Singapore",
    "Slovakia",
    "Slovenia",
    "Solomon Islands",
    "Somalia",
    "South Africa",
    "South Korea",
    "South Sudan",
    "Spain",
    "Sri Lanka",
    "Sudan",
    "Suriname",
    "Sweden",
    "Switzerland",
    "Syria",
    "Taiwan",
    "Tajikistan",
    "Tanzania",
    "Thailand",
    "Timor-Leste",
    "Togo",
    "Tonga",
    "Trinidad and Tobago",
    "Tunisia",
    "Turkey",
    "Turkmenistan",
    "Tuvalu",
    "Uganda",
    "Ukraine",
    "United Arab Emirates",
    "United Kingdom",
    "United States",
    "Uruguay",
    "Uzbekistan",
    "Vanuatu",
    "Vatican City",
    "Venezuela",
    "Vietnam",
    "Yemen",
    "Zambia",
    "Zimbabwe",
)
# Common short forms, matched only in capitals: "us" is a word too.
_SHORT_FORMS: Final = {
    "USA": "United States",
    "US": "United States",
    "UK": "United Kingdom",
    "UAE": "United Arab Emirates",
}
_ANY_COUNTRY: Final = ("Worldwide", "Anywhere")
_CANONICAL: Final = {name.casefold(): name for name in _COUNTRY_NAMES} | {
    word.casefold(): WORLDWIDE for word in _ANY_COUNTRY
}


def _alternatives(names: Iterable[str]) -> str:
    # The longest first, so that "South Sudan" wins over "Sudan" where both start.
    return "|".join(re.escape(name) for name in sorted(names, key=len, reverse=True))


_COUNTRY: Final = re.compile(
    rf"(?<![\w-])(?:(?i:(?P<name>{_alternatives([*_COUNTRY_NAMES, *_ANY_COUNTRY])}))"
    rf"|(?P<short>{_alternatives(_SHORT_FORMS)}))(?![\w-])"
)


def countries(location: str | None) -> list[str]:
    """The known countries the location names, in the order they appear and each once."""
    found: dict[str, None] = {}
    for match in _COUNTRY.finditer(location or ""):
        name, short = match.group("name"), match.group("short")
        found[_CANONICAL[name.casefold()] if name else _SHORT_FORMS[short]] = None
    return list(found)
