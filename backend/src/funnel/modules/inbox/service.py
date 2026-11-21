from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, time
from typing import Any, Final
from uuid import UUID

import httpx2
import structlog

from funnel.core.exceptions import NotFoundError
from funnel.core.pagination import PageParams
from funnel.modules.applications.domain import Channel
from funnel.modules.applications.schemas import ApplicationCreate
from funnel.modules.applications.service import ApplicationService
from funnel.modules.companies.service import CompanyService
from funnel.modules.discovery.domain import (
    Feed,
    ImportMethod,
    SearchTerms,
    WorkMode,
    next_import_at,
)
from funnel.modules.discovery.service import JobBoardService, SearchProfileService
from funnel.modules.inbox.alerts import read_alert
from funnel.modules.inbox.ats import BoardReader
from funnel.modules.inbox.domain import (
    LATEST_ONLY_FEEDS,
    TRIAGE_DECISIONS,
    TRIAGE_MISTAKES,
    WHY_LENGTH,
    BoardUnavailableError,
    CriteriaPreview,
    DiscardReason,
    EmailAlertNotImportedError,
    FeedCooldownError,
    FeedOffer,
    FeedUnavailableError,
    FilteredCounts,
    FrequentTitle,
    ImportedByEmailError,
    JobBoardNotImportedError,
    OfferAction,
    OfferFilter,
    OfferNotFilteredError,
    OfferQuality,
    OfferReaderError,
    OfferReaderUnavailableError,
    OfferStatus,
    OfferText,
    OfferTriagerError,
    OfferTriagerUnavailableError,
    ProfileRule,
    Reading,
    Relaxing,
    Review,
    Rule,
    RuleChangedSinceError,
    RuleCheck,
    RuleResult,
    SuggestionSource,
    Triage,
    TriageContext,
    TriageReply,
    TriagerSuggestion,
    Verdict,
    WordNotInTitleError,
    can_change,
    can_exclude,
    count_filtered,
    duplicate_key,
    exclusion_candidates,
    frequent_titles,
    holds_the_rule,
    is_relaxing,
    is_title_word,
    kept_suggestion,
    kept_triage,
    next_status,
    offer_quality,
    plain_text,
    preview_criteria,
    quality_starts_on,
    relaxing,
    rule_after,
    supported,
    url_key,
    variant_key,
)
from funnel.modules.inbox.feeds import FeedReader
from funnel.modules.inbox.models import CriteriaChangeRow, OfferRow, WatchedCompanyRow
from funnel.modules.inbox.reader import Reader
from funnel.modules.inbox.repository import (
    CriteriaChangeRepository,
    FeedImportRepository,
    OfferRepository,
    ReadingRepository,
    SuggestionRepository,
    TriageRepository,
    WatchedCompanyRepository,
)
from funnel.modules.inbox.schemas import (
    CriteriaChangeCreate,
    OfferCreate,
    WatchedCompanyCreate,
)
from funnel.modules.inbox.triager import Triager

_logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class FrequentTitles:
    """How many offers have no title of the profile, and their most frequent titles with
    the profile's titles if each were added and what that would do."""

    offers: int
    titles: list[tuple[FrequentTitle, list[str], CriteriaPreview]]


class OfferService:
    """Status rules come from the domain; promoting goes through the other modules' services.
    The search profiles decide which offers are filtered."""

    def __init__(  # noqa: PLR0913, PLR0917  # one collaborator each, wired in the router
        self,
        repository: OfferRepository,
        profiles: SearchProfileService,
        companies: CompanyService,
        applications: ApplicationService,
    ) -> None:
        self._repository = repository
        self._profiles = profiles
        self._companies = companies
        self._applications = applications

    async def create(self, offer: OfferCreate) -> OfferRow:
        row = OfferRow(
            **offer.model_dump(),
            duplicate_key=duplicate_key(offer.company, offer.title),
            variant_key=variant_key(offer.company, offer.title),
            url_key=url_key(offer.url),
            status=OfferStatus.PENDING,
        )
        return await self._repository.add(row, await self._profiles.all_terms())

    async def get(self, offer_id: UUID) -> OfferRow:
        offer = await self._repository.get(offer_id, await self._profiles.all_terms())
        if offer is None:
            raise NotFoundError(f"Offer {offer_id} does not exist")
        return offer

    async def list_page(
        self, offer_filter: OfferFilter, page: PageParams
    ) -> tuple[list[OfferRow], int]:
        profiles = await self._profiles.all_terms()
        return await self._repository.list_page(offer_filter, page, profiles)

    async def near_miss_groups(self, limit: int) -> list[tuple[Rule, int, list[OfferRow]]]:
        return await self._repository.near_miss_groups(await self._profiles.all_terms(), limit)

    async def count_filtered(self) -> FilteredCounts:
        profiles = await self._profiles.all_terms()
        return count_filtered(
            await self._repository.all_reasons(profiles), await self._repository.all_reviews()
        )

    async def quality(self, now: datetime) -> OfferQuality:
        """The offer quality of the 4 weeks up to now, with the applications of the promoted."""
        starts_on = quality_starts_on(now.date())
        since = datetime.combine(starts_on, time(), now.tzinfo)
        added = await self._repository.added_since(since, await self._profiles.all_terms())
        stages = await self._applications.stages(
            [application_id for _, application_id in added if application_id is not None]
        )
        offers = [
            replace(offer, stage=stages.get(application_id)) if application_id else offer
            for offer, application_id in added
        ]
        counts = await self.count_filtered()
        return offer_quality(offers, now.date(), counts.near_misses)

    async def frequent_titles(self, profile_id: UUID) -> FrequentTitles:
        """The titles that keep coming among the offers filtered without a title of the
        profile, each with what adding it would do."""
        await self._profiles.get(profile_id)
        profiles = await self._profiles.all_terms()
        terms = next(terms for terms in profiles if terms.search_profile_id == profile_id)
        untitled = await self._repository.without_a_title_of(terms, profiles)
        titles = []
        for title in frequent_titles(untitled):
            adding = [*terms.titles, title.title]
            titles.append((title, adding, await self.preview(profile_id, {"titles": adding})))
        return FrequentTitles(len(untitled), titles)

    async def preview(self, profile_id: UUID, changes: Mapping[str, Any]) -> CriteriaPreview:
        """What editing the profile with these changes would do to the offers; saves nothing."""
        await self._profiles.get(profile_id)
        current = await self._profiles.all_terms()
        changed = [
            replace(terms, **changes) if terms.search_profile_id == profile_id else terms
            for terms in current
        ]
        return preview_criteria(await self._repository.fit_changes(current, changed))

    async def mark_rightly_filtered(self, offer_id: UUID) -> OfferRow:
        offer = await self.get(offer_id)
        failed = _failed_rules(offer)
        if not failed:
            raise OfferNotFilteredError(f"Offer {offer_id} is not filtered")
        offer.review = Review.RIGHTLY_FILTERED
        offer.review_rules = failed
        return await self._repository.save(offer, await self._profiles.all_terms())

    async def unmark_rightly_filtered(self, offer_id: UUID) -> None:
        offer = await self.get(offer_id)
        if offer.review is Review.RIGHTLY_FILTERED:
            offer.review = None
            offer.review_rules = []
            await self._repository.save(offer, await self._profiles.all_terms())

    async def discard(self, offer_id: UUID, reason: DiscardReason, word: str | None) -> OfferRow:
        offer = await self.get(offer_id)
        offer.status = next_status(offer.status, OfferAction.DISCARD)
        if word is not None and not is_title_word(word, offer.title):
            raise WordNotInTitleError(f"{word!r} is not a word of {offer.title!r}")
        offer.discard_reason = reason
        offer.discard_word = word
        return await self._repository.save(offer, await self._profiles.all_terms())

    async def restore(self, offer_id: UUID) -> None:
        offer = await self.get(offer_id)
        offer.status = next_status(offer.status, OfferAction.RESTORE)
        offer.discard_reason = None
        offer.discard_word = None
        await self._repository.save(offer, await self._profiles.all_terms())

    async def promote(self, offer_id: UUID, channel: Channel) -> OfferRow:
        offer = await self.get(offer_id)
        status = next_status(offer.status, OfferAction.PROMOTE)
        company = await self._companies.find_or_create(offer.company)
        application = await self._applications.create(
            ApplicationCreate(
                company_id=company.id, role=offer.title, channel=channel, url=offer.url
            )
        )
        # Promoting a filtered offer is a rescue: it keeps the rules that filtered it.
        failed = _failed_rules(offer)
        offer.review = Review.RESCUED if failed else None
        offer.review_rules = failed
        offer.status = status
        offer.application_id = application.id
        return await self._repository.save(offer, await self._profiles.all_terms())


class CriteriaChangeService:
    """Changes one rule of a profile through its service, logged with what it did."""

    def __init__(
        self,
        repository: CriteriaChangeRepository,
        offers: OfferService,
        profiles: SearchProfileService,
    ) -> None:
        self._repository = repository
        self._offers = offers
        self._profiles = profiles

    async def make(self, change: CriteriaChangeCreate) -> CriteriaChangeRow:
        ((rule, value),) = change.rules().items()
        profile_id, offer_id = change.search_profile_id, change.offer_id
        profile = await self._profiles.get(profile_id)
        if offer_id is not None:
            await self._offers.get(offer_id)
        before = _as_json(getattr(profile, rule))
        preview = await self._offers.preview(profile_id, {rule: _as_terms(rule, value)})
        await self._profiles.update(profile_id, {rule: value})
        return await self._repository.add(
            CriteriaChangeRow(
                search_profile_id=profile_id,
                offer_id=offer_id,
                rule=rule,
                before=before,
                after=value,
                entering_pending=preview.entering_pending,
                leaving_pending=preview.leaving_pending,
                promoted_filtered=preview.promoted_filtered,
                discarded_filtered=preview.discarded_filtered,
            )
        )

    async def undo(self, change_id: UUID) -> None:
        change = await self._repository.get(change_id)
        if change is None:
            raise NotFoundError(f"Criteria change {change_id} does not exist")
        if await self._repository.is_changed_since(change):
            raise RuleChangedSinceError(f"The {change.rule} changed after change {change_id}")
        await self._profiles.update(change.search_profile_id, {change.rule: change.before})
        await self._repository.delete(change)

    async def list_page(self, page: PageParams) -> tuple[list[CriteriaChangeRow], int]:
        return await self._repository.list_page(page)


@dataclass(frozen=True)
class CriteriaSuggestion:
    """Excluding a word from a profile, with the discards behind it and what it would do."""

    search_profile_id: UUID
    search_profile_name: str
    word: str
    after: list[str]
    offer_ids: list[UUID]
    discarded: int
    preview: CriteriaPreview
    source: SuggestionSource = SuggestionSource.COUNT
    why: str | None = None
    rule: ProfileRule = ProfileRule.EXCLUDED_KEYWORDS


class CriteriaSuggestionService:
    """Counts the user's decisions to suggest exclusions; never applies one."""

    def __init__(
        self,
        repository: SuggestionRepository,
        offers: OfferService,
        profiles: SearchProfileService,
    ) -> None:
        self._repository = repository
        self._offers = offers
        self._profiles = profiles

    async def list_all(self) -> list[CriteriaSuggestion]:
        discarded = await self._repository.discarded_titles()
        candidates = exclusion_candidates(discarded, await self._repository.promoted_titles())
        dismissed = await self._repository.dismissed()
        suggestions: list[CriteriaSuggestion] = []
        for terms in await self._profiles.all_terms():
            assert terms.search_profile_id is not None  # all_terms reads saved profiles
            for candidate in candidates:
                word, profile_id = candidate.word, terms.search_profile_id
                key = (profile_id, ProfileRule.EXCLUDED_KEYWORDS, word.casefold())
                if key in dismissed or not can_exclude(word, terms):
                    continue
                excluding = [*terms.excluded_keywords, word]
                preview = await self._offers.preview(profile_id, {"excluded_keywords": excluding})
                if preview.discarded_filtered > 0:
                    suggestions.append(
                        CriteriaSuggestion(
                            profile_id,
                            terms.name,
                            word,
                            excluding,
                            list(candidate.offer_ids),
                            len(discarded),
                            preview,
                        )
                    )
        return suggestions + await self._from_triager(suggestions, dismissed, len(discarded))

    async def _from_triager(
        self,
        counted: Sequence[CriteriaSuggestion],
        dismissed: Collection[tuple[UUID, ProfileRule, str]],
        discarded: int,
    ) -> list[CriteriaSuggestion]:
        """The triager's suggestions that still hold the rule and were not counted too."""
        terms_by_id = {t.search_profile_id: t for t in await self._profiles.all_terms()}
        seen = {(s.search_profile_id, s.rule, s.word.casefold()) for s in counted}
        suggestions: list[CriteriaSuggestion] = []
        for row in await self._repository.triager_suggestions():
            key = (row.search_profile_id, row.rule, row.word.casefold())
            terms = terms_by_id.get(row.search_profile_id)
            if key in seen or key in dismissed or terms is None:
                continue
            if not can_change(terms, row.rule, row.word):
                continue
            after = rule_after(terms, row.rule, row.word)
            preview = await self._offers.preview(row.search_profile_id, {row.rule: after})
            if holds_the_rule(preview, relaxing=is_relaxing(terms, row.rule, row.word)):
                suggestions.append(
                    CriteriaSuggestion(
                        row.search_profile_id,
                        terms.name,
                        row.word,
                        after,
                        list(row.offer_ids),
                        discarded,
                        preview,
                        SuggestionSource.TRIAGER,
                        row.why,
                        row.rule,
                    )
                )
        return suggestions

    async def dismiss(self, profile_id: UUID, rule: ProfileRule, word: str) -> None:
        await self._profiles.get(profile_id)
        await self._repository.dismiss(profile_id, rule, word)


def _as_json(value: Any) -> Any:
    """A rule's value as the log keeps it: lists of plain strings, or the location."""
    return [str(item) for item in value] if isinstance(value, list) else value


def _as_terms(rule: ProfileRule, value: Any) -> Any:
    """The value as a profile's terms take it: work modes as their enum."""
    return [WorkMode(mode) for mode in value] if rule is ProfileRule.WORK_MODES else value


def _failed_rules(offer: OfferRow) -> list[str]:
    """The rules that filter the offer now; none if it is not filtered."""
    return [str(rule) for rule in offer.filter_reason.failed] if offer.filter_reason else []


@dataclass(frozen=True)
class ReadingBatch:
    read: int
    failed: int
    left: int


class OfferReadingService:
    """Has the offer reader read the offers the search profiles fit by their words."""

    def __init__(
        self,
        readings: ReadingRepository,
        profiles: SearchProfileService,
        reader: Reader | None,
    ) -> None:
        self._readings = readings
        self._profiles = profiles
        self._reader = reader

    async def read_pending(self) -> ReadingBatch:
        if self._reader is None:
            raise OfferReaderUnavailableError("No offer reader is configured")
        profiles = await self._profiles.all_terms()
        unread, total = await self._readings.list_unread(profiles, self._reader.batch_size)
        questions = [
            (
                OfferText(
                    offer.title,
                    offer.company,
                    plain_text(offer.description or ""),
                    location=offer.location,
                ),
                location,
            )
            for offer, location in unread
        ]
        answers: list[Reading | OfferReaderError]
        try:
            answers = await self._reader.read_batch(questions)
        except OfferReaderError as error:
            answers = [error] * len(questions)
        read = 0
        for (offer, location), (text, _), answer in zip(unread, questions, answers, strict=True):
            if isinstance(answer, OfferReaderError):
                # Left unread: the next reading tries it again.
                _logger.warning("offer_reading_failed", offer_id=str(offer.id), error=str(answer))
                continue
            kept = supported(answer, text.evidence, asked_location=location is not None)
            await self._readings.add(offer.id, location, kept)
            read += 1
        return ReadingBatch(read=read, failed=len(unread) - read, left=total - read)


@dataclass(frozen=True)
class TriageBatch:
    triaged: int
    failed: int
    left: int
    ok: int = 0
    ko: int = 0
    to_rescue: int = 0


# The near misses are decided by the domain: the triage reads them all.
_ALL: Final = 100_000


def _why_yes(triage: Triage) -> str:
    """Why a near miss is worth rescuing: the why of a suggestion to relax its rule."""
    return "" if triage.why_yes is None else triage.why_yes.why


def _failed_check(offer: OfferRow) -> RuleCheck | None:
    """The rule that filtered a near miss."""
    reason = offer.filter_reason
    return (
        next((c for c in reason.rules if c.result is RuleResult.FAILED), None) if reason else None
    )


class OfferTriageService:
    """Has the offer triager compare the pending offers with the user's decisions."""

    def __init__(  # noqa: PLR0913, PLR0917  # one collaborator each, wired in the router
        self,
        triages: TriageRepository,
        suggestions: SuggestionRepository,
        offers: OfferService,
        profiles: SearchProfileService,
        triager: Triager | None,
    ) -> None:
        self._triages = triages
        self._suggestions = suggestions
        self._offers = offers
        self._profiles = profiles
        self._triager = triager

    @property
    def is_available(self) -> bool:
        return self._triager is not None

    async def _near_misses(self) -> list[OfferRow]:
        """The near misses with a description and no verdict, the most recent first."""
        near_misses, _ = await self._offers.list_page(
            OfferFilter(OfferStatus.PENDING, is_filtered=True, is_near_miss=True),
            PageParams(limit=_ALL, offset=0),
        )
        return [o for o in near_misses if o.verdict is None and (o.description or "").strip()]

    async def triage_pending(self) -> TriageBatch:
        if self._triager is None:
            raise OfferTriagerUnavailableError("No offer triager is configured")
        profiles = await self._profiles.all_terms()
        size = self._triager.batch_size
        fitting, total = await self._triages.list_untriaged(profiles, size)
        near_misses = await self._near_misses()
        offers = [*fitting, *near_misses[: size - len(fitting)]]
        total += len(near_misses)
        if not offers:
            return TriageBatch(triaged=0, failed=0, left=total)
        context = TriageContext(
            profiles,
            await self._triages.decisions(TRIAGE_DECISIONS),
            await self._triages.mistakes(TRIAGE_MISTAKES),
        )
        texts = [
            OfferText(
                offer.title,
                offer.company,
                plain_text(offer.description or ""),
                _failed_check(offer) if number >= len(fitting) else None,
                offer.location,
            )
            for number, offer in enumerate(offers)
        ]
        try:
            reply = await self._triager.triage(texts, context)
        except OfferTriagerError as error:
            # Left untriaged: the next triage tries them again.
            _logger.warning("offer_triage_failed", offers=len(offers), error=str(error))
            reply = TriageReply({})
        verdicts: dict[int, Verdict] = {}
        for number, answer in reply.answers.items():
            triage = kept_triage(answer, texts[number])
            if triage is None:
                continue
            verdicts[number] = triage.verdict
            check = texts[number].filtered_by
            # A near miss is never suggested for discard: KO is rightly filtered.
            discard = None if check else kept_suggestion(answer, texts[number])
            await self._triages.save(offers[number], triage, discard)
            if check and triage.verdict is Verdict.OK:
                await self._relax(offers[number], relaxing(check), triage)
        for suggestion in reply.suggestions:
            await self._keep(suggestion, profiles, offers, texts, verdicts)
        said = [verdicts[n] for n in verdicts if n < len(fitting)]
        to_rescue = sum(verdicts[n] is Verdict.OK for n in verdicts if n >= len(fitting))
        triaged = len(verdicts)
        return TriageBatch(
            triaged=triaged,
            failed=len(offers) - triaged,
            left=total - triaged,
            ok=said.count(Verdict.OK),
            ko=said.count(Verdict.KO),
            to_rescue=to_rescue,
        )

    async def _relax(self, offer: OfferRow, change: Relaxing | None, triage: Triage) -> None:
        """Keep the suggestion to relax the rule that filtered an OK near miss, for its
        reference profile, if it holds the rule for relaxing a criterion."""
        reason = offer.filter_reason
        if change is None or reason is None or reason.search_profile_id is None:
            return
        await self._keep_change(
            reason.search_profile_id, change.rule, change.word, _why_yes(triage), [offer.id]
        )

    async def _keep_change(  # noqa: PLR0913, PLR0917  # the parts of a suggestion
        self,
        profile_id: UUID,
        rule: ProfileRule,
        word: str,
        why: str,
        offer_ids: Sequence[UUID],
    ) -> None:
        terms = next(
            (t for t in await self._profiles.all_terms() if t.search_profile_id == profile_id),
            None,
        )
        if terms is None or not can_change(terms, rule, word):
            return
        if (profile_id, rule, word.casefold()) in await self._suggestions.dismissed():
            return
        preview = await self._offers.preview(profile_id, {rule: rule_after(terms, rule, word)})
        if holds_the_rule(preview, relaxing=is_relaxing(terms, rule, word)):
            await self._suggestions.keep_triager_suggestion(
                profile_id, rule, word, " ".join(why.split())[:WHY_LENGTH], offer_ids
            )

    async def _keep(  # noqa: PLR0913, PLR0917  # what the batch knows of each offer
        self,
        suggestion: TriagerSuggestion,
        profiles: Sequence[SearchTerms],
        offers: Sequence[OfferRow],
        texts: Sequence[OfferText],
        verdicts: Mapping[int, Verdict],
    ) -> None:
        """Keep a suggested exclusion if it comes from KO offers with the word and holds the
        rule: it would filter no promoted offer and at least one discarded."""
        word = suggestion.word.strip()
        terms = next(
            (t for t in profiles if t.name.casefold() == suggestion.profile.casefold()), None
        )
        from_offers = [
            offers[number].id
            for number in dict.fromkeys(suggestion.offers)
            if verdicts.get(number) is Verdict.KO
            and is_title_word(word, f"{texts[number].title}\n{texts[number].description}")
        ]
        if not word or terms is None or not from_offers or not can_exclude(word, terms):
            return
        assert terms.search_profile_id is not None  # all_terms reads saved profiles
        await self._keep_change(
            terms.search_profile_id,
            ProfileRule.EXCLUDED_KEYWORDS,
            word,
            suggestion.why,
            from_offers,
        )


@dataclass(frozen=True)
class ImportResult:
    job_board_id: UUID
    found: int
    added: int
    filtered: int
    expired: int
    imported_at: datetime


class FeedImportService:
    """Reads the feed of a job board and fills the inbox, within the limits of the feed's
    terms."""

    def __init__(  # noqa: PLR0913, PLR0917  # one collaborator each, wired in the router
        self,
        imports: FeedImportRepository,
        profiles: SearchProfileService,
        job_boards: JobBoardService,
        reader: FeedReader,
    ) -> None:
        self._imports = imports
        self._profiles = profiles
        self._job_boards = job_boards
        self._reader = reader

    async def import_job_board(self, job_board_id: UUID, now: datetime) -> ImportResult:
        job_board = await self._job_boards.get(job_board_id)
        if job_board.import_method is ImportMethod.NONE:
            raise JobBoardNotImportedError(f"The job board {job_board.name} is not imported")
        if job_board.import_method is ImportMethod.EMAIL:
            raise ImportedByEmailError(f"{job_board.name} is imported from its email alerts")
        last = job_board.last_imported_at
        if last is not None and now < next_import_at(last):
            raise FeedCooldownError(job_board.name, next_import_at(last), now)

        profiles = await self._profiles.all_terms()
        titles = list(dict.fromkeys(title for terms in profiles for title in terms.titles))
        try:
            published = await self._read(job_board.feed, job_board.rss_url_template, titles)
        except (httpx2.HTTPError, ValueError, KeyError, TypeError) as error:
            # Network failure, error status or an unexpected shape: the source is unusable now.
            raise FeedUnavailableError(f"{job_board.name} could not be read") from error
        added = await self._imports.add_new(
            [_offer_row(offer, job_board_id=job_board.id) for offer in published]
        )
        filtered = await self._imports.count_filtered(added, profiles)
        expired = (
            0
            if job_board.feed in LATEST_ONLY_FEEDS
            else await self._imports.expire_missing(
                job_board.id, [offer.url for offer in published]
            )
        )
        # Only a successful read counts for the limit: a failed one can be retried at once.
        await self._job_boards.record_import(job_board, now)
        return ImportResult(job_board.id, len(published), len(added), filtered, expired, now)

    async def _read(
        self, feed: Feed | None, rss_url_template: str | None, titles: list[str]
    ) -> list[FeedOffer]:
        if feed is not None:
            return await self._reader.read(feed, titles)
        # The schemas and a CHECK give every imported job board a feed or an RSS.
        assert rss_url_template is not None
        return await self._reader.read_rss(rss_url_template, titles)


@dataclass(frozen=True)
class AlertImportResult:
    job_board_id: UUID
    found: int
    added: int
    filtered: int
    imported_at: datetime


class EmailAlertService:
    """Imports the offers of a job alert email into the job board that imports the alert.

    No limit and no expiry: each alert is a new email that lists only new offers.
    """

    def __init__(
        self,
        imports: FeedImportRepository,
        profiles: SearchProfileService,
        job_boards: JobBoardService,
    ) -> None:
        self._imports = imports
        self._profiles = profiles
        self._job_boards = job_boards

    async def import_alert(self, sender: str, text: str, now: datetime) -> AlertImportResult:
        email_alert, offers = read_alert(sender, text)
        job_board = await self._job_boards.find_by_email_alert(email_alert)
        if job_board is None:
            raise EmailAlertNotImportedError(f"No job board imports the {email_alert} alerts")
        added = await self._imports.add_new(
            [_offer_row(offer, job_board_id=job_board.id) for offer in offers]
        )
        filtered = await self._imports.count_filtered(added, await self._profiles.all_terms())
        return AlertImportResult(job_board.id, len(offers), len(added), filtered, now)


@dataclass(frozen=True)
class BoardImportResult:
    watched_company_id: UUID
    found: int
    added: int
    filtered: int
    expired: int
    imported_at: datetime


class WatchedCompanyService:
    """Watched companies, and importing their ATS boards into the inbox (no rate limit)."""

    def __init__(
        self,
        companies: WatchedCompanyRepository,
        profiles: SearchProfileService,
        reader: BoardReader,
    ) -> None:
        self._companies = companies
        self._profiles = profiles
        self._reader = reader

    async def create(self, company: WatchedCompanyCreate) -> WatchedCompanyRow:
        return await self._companies.add(WatchedCompanyRow(**company.model_dump()))

    async def list_all(self) -> list[WatchedCompanyRow]:
        return await self._companies.list_all()

    async def get(self, company_id: UUID) -> WatchedCompanyRow:
        company = await self._companies.get(company_id)
        if company is None:
            raise NotFoundError(f"Watched company {company_id} does not exist")
        return company

    async def delete(self, company_id: UUID) -> None:
        await self._companies.delete(await self.get(company_id))

    async def import_board(self, company_id: UUID, now: datetime) -> BoardImportResult:
        company = await self.get(company_id)
        published = await self._read(company)
        added = await self._companies.add_new_offers(
            [_offer_row(offer, watched_company_id=company.id) for offer in published]
        )
        filtered = await self._companies.count_filtered(added, await self._profiles.all_terms())
        expired = await self._companies.expire_missing_offers(
            company.id, [offer.url for offer in published]
        )
        return BoardImportResult(company.id, len(published), len(added), filtered, expired, now)

    async def _read(self, company: WatchedCompanyRow) -> list[FeedOffer]:
        try:
            return await self._reader.read(company.ats, company.board, company.name)
        except (httpx2.HTTPError, ValueError, KeyError, TypeError) as error:
            # Network failure, error status (404: unknown board) or an unexpected shape.
            raise BoardUnavailableError(
                f"The {company.ats} board {company.board} could not be read"
            ) from error


def _offer_row(
    offer: FeedOffer, *, job_board_id: UUID | None = None, watched_company_id: UUID | None = None
) -> OfferRow:
    return OfferRow(
        url=offer.url,
        company=offer.company,
        title=offer.title,
        description=offer.description,
        location=offer.location,
        duplicate_key=duplicate_key(offer.company, offer.title),
        variant_key=variant_key(offer.company, offer.title),
        url_key=url_key(offer.url),
        status=OfferStatus.PENDING,
        job_board_id=job_board_id,
        watched_company_id=watched_company_id,
    )
