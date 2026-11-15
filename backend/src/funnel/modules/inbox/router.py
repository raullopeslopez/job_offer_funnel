from collections.abc import AsyncIterator
from dataclasses import asdict
from http import HTTPStatus
from typing import Annotated, Any
from uuid import UUID

import httpx2
from fastapi import APIRouter, Depends, Query, Request

from funnel.core.clock import Clock, get_clock
from funnel.core.config import Settings
from funnel.core.db import SessionDep
from funnel.core.errors import ProblemRead, ValidationProblemRead
from funnel.core.pagination import Page, PageParams, get_page_params
from funnel.modules.applications.service import build_application_service
from funnel.modules.companies.service import build_company_service
from funnel.modules.discovery.service import (
    build_job_board_service,
    build_search_profile_service,
)
from funnel.modules.inbox.ats import BoardReader
from funnel.modules.inbox.domain import OfferFilter, OfferStatus, Rule
from funnel.modules.inbox.feeds import FeedReader
from funnel.modules.inbox.reader import OfferReader
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
    AlertEmailCreate,
    AlertImportRead,
    BoardImportRead,
    CriteriaChangeCreate,
    CriteriaChangeRead,
    CriteriaPreviewCreate,
    CriteriaPreviewRead,
    CriteriaSuggestionRead,
    DiscardCreate,
    DiscardReasonCountRead,
    DismissalCreate,
    DismissalRead,
    FilteredCountsRead,
    FrequentTitleRead,
    FrequentTitlesRead,
    ImportRead,
    OfferCreate,
    OfferQualityRead,
    OfferRead,
    PromotionCreate,
    QualityFiguresRead,
    ReadingBatchRead,
    SourceQualityRead,
    TriageBatchRead,
    TriagerRead,
    WatchedCompanyCreate,
    WatchedCompanyRead,
    WeekQualityRead,
)
from funnel.modules.inbox.service import (
    CriteriaChangeService,
    CriteriaSuggestionService,
    EmailAlertService,
    FeedImportService,
    OfferReadingService,
    OfferService,
    OfferTriageService,
    WatchedCompanyService,
)
from funnel.modules.inbox.triager import OfferTriager

offers_router = APIRouter(prefix="/offers", tags=["inbox"])


def get_offer_service(
    session: SessionDep,
    clock: Annotated[Clock, Depends(get_clock)],
) -> OfferService:
    # Composition root. One session for all the services: promoting is all or nothing.
    return OfferService(
        OfferRepository(session),
        build_search_profile_service(session),
        build_company_service(session),
        build_application_service(session, clock),
    )


Service = Annotated[OfferService, Depends(get_offer_service)]

_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    HTTPStatus.NOT_FOUND: {"model": ProblemRead, "description": "Offer does not exist"}
}
_WRONG_STATUS: dict[int | str, dict[str, Any]] = {
    HTTPStatus.CONFLICT: {
        "model": ProblemRead,
        "description": "Not allowed in the offer's current status (`invalid-offer-status`)",
    }
}


# Identifies the app to the feeds, as their terms expect; no personal data.
USER_AGENT = "job-offer-funnel"
FEED_TIMEOUT_SECONDS = 20


async def get_feed_client() -> AsyncIterator[httpx2.AsyncClient]:
    """HTTP client for the public feeds; tests replace it so they never reach the internet."""
    async with httpx2.AsyncClient(
        timeout=FEED_TIMEOUT_SECONDS, headers={"User-Agent": USER_AGENT}
    ) as client:
        yield client


def get_offer_reader(
    request: Request, client: Annotated[httpx2.AsyncClient, Depends(get_feed_client)]
) -> OfferReader | None:
    """The offer reader, or None without its API key; tests replace it with a fake."""
    settings: Settings = request.app.state.settings
    api_key = settings.groq_api_key.get_secret_value()
    return OfferReader(client, api_key, settings.groq_model) if api_key else None


def get_offer_reading_service(
    session: SessionDep, reader: Annotated[OfferReader | None, Depends(get_offer_reader)]
) -> OfferReadingService:
    return OfferReadingService(
        ReadingRepository(session), build_search_profile_service(session), reader
    )


def get_offer_triager(
    request: Request, client: Annotated[httpx2.AsyncClient, Depends(get_feed_client)]
) -> OfferTriager | None:
    """The offer triager, or None without its API key; tests replace it with a fake."""
    settings: Settings = request.app.state.settings
    api_key = settings.groq_api_key.get_secret_value()
    return OfferTriager(client, api_key, settings.groq_model) if api_key else None


def get_offer_triage_service(
    session: SessionDep,
    offers: Annotated[OfferService, Depends(get_offer_service)],
    triager: Annotated[OfferTriager | None, Depends(get_offer_triager)],
) -> OfferTriageService:
    return OfferTriageService(
        TriageRepository(session),
        SuggestionRepository(session),
        offers,
        build_search_profile_service(session),
        triager,
    )


TriageService = Annotated[OfferTriageService, Depends(get_offer_triage_service)]


@offers_router.post(
    "",
    status_code=HTTPStatus.CREATED,
    responses={
        HTTPStatus.CONFLICT: {
            "model": ProblemRead,
            "description": "An offer with the same company and title, or the same URL, "
            "already exists, even if discarded (`already-exists`)",
        },
        HTTPStatus.UNPROCESSABLE_CONTENT: {
            "model": ValidationProblemRead | ProblemRead,
            "description": "Invalid body (`validation-error`), or the job board does not "
            "exist (`unknown-job-board`)",
        },
    },
)
async def create_offer(offer: OfferCreate, service: Service) -> OfferRead:
    """Add an offer to the inbox, as pending. Company and title identify it."""
    created = await service.create(offer)
    return OfferRead.model_validate(created, from_attributes=True)


@offers_router.get("")
async def list_offers(  # noqa: PLR0913, PLR0917  # FastAPI injects each input as a parameter
    page: Annotated[PageParams, Depends(get_page_params)],
    service: Service,
    status: Annotated[OfferStatus | None, Query()] = None,
    filtered: Annotated[
        bool | None, Query(description="Only the filtered offers (true) or the others (false).")
    ] = None,
    near_miss: Annotated[
        bool | None, Query(description="Only the near misses (true) or the others (false).")
    ] = None,
    failed_rule: Annotated[
        Rule | None, Query(description="Only the offers whose filter reason fails this rule.")
    ] = None,
) -> Page[OfferRead]:
    """Offers from the most recently added."""
    offers, total = await service.list_page(
        OfferFilter(status, filtered, near_miss, failed_rule), page
    )
    return Page(
        items=[OfferRead.model_validate(row, from_attributes=True) for row in offers],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@offers_router.post(
    "/readings",
    status_code=HTTPStatus.CREATED,
    responses={
        HTTPStatus.SERVICE_UNAVAILABLE: {
            "model": ProblemRead,
            "description": "No offer reader is configured (`offer-reader-unavailable`); "
            "nothing changed",
        },
    },
)
async def read_offers(
    service: Annotated[OfferReadingService, Depends(get_offer_reading_service)],
) -> ReadingBatchRead:
    """Have the offer reader read up to 5 pending imported offers: their work mode, whether
    they can be done living in the location of the search profiles they fit, and whether
    they are stable jobs. What a reading says filters the offer like the profile's words.

    An offer is read once for each location of the profiles it fits by its words; offers
    without a description are never read. Call it again while `left` is not 0; an offer
    the reader fails on is left to be read.
    """
    batch = await service.read_pending()
    return ReadingBatchRead(read=batch.read, failed=batch.failed, left=batch.left)


@offers_router.get("/triager")
async def read_offer_triager(service: TriageService) -> TriagerRead:
    """Whether the offers can be triaged: without an offer triager the app works as always."""
    return TriagerRead(is_available=service.is_available)


@offers_router.post(
    "/triages",
    status_code=HTTPStatus.CREATED,
    responses={
        HTTPStatus.SERVICE_UNAVAILABLE: {
            "model": ProblemRead,
            "description": "No offer triager is configured (`offer-triager-unavailable`); "
            "nothing changed",
        },
    },
)
async def triage_offers(service: TriageService) -> TriageBatchRead:
    """Have the offer triager compare the pending imported offers that fit a profile, up to
    5 with Groq and 20 with Claude Code, in a single request, with your promoted and
    discarded offers and its own mistakes. It marks each one `ok` or `ko` (a false
    positive), with why; a `ko` may suggest a discard, with a reason and its evidence. It
    may also suggest excluding a word from a profile, which joins the criteria suggestions
    if it holds the rule. Then the near misses go, the same way: `ok` is a false negative
    (`to_rescue`), and it may suggest relaxing the rule that filtered it. Nothing is
    applied.

    An offer is triaged once. Call it again while `left` is not 0; the offers the triager
    does not answer for are left to triage.
    """
    batch = await service.triage_pending()
    return TriageBatchRead(
        triaged=batch.triaged,
        ok=batch.ok,
        ko=batch.ko,
        to_rescue=batch.to_rescue,
        failed=batch.failed,
        left=batch.left,
    )


@offers_router.get("/filtered-counts")
async def count_filtered_offers(service: Service) -> FilteredCountsRead:
    """How many pending offers are filtered, how many are near misses and how many fail
    each rule of their filter reason."""
    counts = await service.count_filtered()
    return FilteredCountsRead(
        filtered=counts.filtered,
        near_misses=counts.near_misses,
        failing=dict(counts.failing),
        reviewed_near_misses=counts.reviewed_near_misses,
        rescued_near_misses=counts.rescued_near_misses,
    )


@offers_router.post(
    "/criteria-previews",
    responses={
        HTTPStatus.NOT_FOUND: {"model": ProblemRead, "description": "Profile does not exist"}
    },
)
async def preview_criteria(preview: CriteriaPreviewCreate, service: Service) -> CriteriaPreviewRead:
    """What editing a search profile would do to the offers, saving nothing (hence 200)."""
    changes = preview.model_dump(exclude_unset=True, exclude={"search_profile_id", "name"})
    result = await service.preview(preview.search_profile_id, changes)
    return CriteriaPreviewRead.model_validate(result, from_attributes=True)


@offers_router.get(
    "/frequent-titles",
    responses={
        HTTPStatus.NOT_FOUND: {"model": ProblemRead, "description": "Profile does not exist"}
    },
)
async def list_frequent_titles(
    search_profile_id: Annotated[UUID, Query()], service: Service
) -> FrequentTitlesRead:
    """The titles that keep coming among the offers filtered with none of the profile's
    titles, and what adding each would do."""
    found = await service.frequent_titles(search_profile_id)
    return FrequentTitlesRead(
        offers=found.offers,
        titles=[
            FrequentTitleRead(
                **asdict(title),
                titles=adding,
                preview=CriteriaPreviewRead.model_validate(preview, from_attributes=True),
            )
            for title, adding, preview in found.titles
        ],
    )


@offers_router.get("/quality")
async def read_offer_quality(
    service: Service, clock: Annotated[Clock, Depends(get_clock)]
) -> OfferQualityRead:
    """Whether what reaches Pending is worth your time, and whether what is worth your time
    reaches Pending: the offers added in the last 4 weeks, in total and week by week."""
    quality = await service.quality(clock.now())
    return OfferQualityRead(
        starts_on=quality.starts_on,
        total=QualityFiguresRead.model_validate(quality.total, from_attributes=True),
        weeks=[
            WeekQualityRead.model_validate(
                {"starts_on": starts_on, **asdict(figures)}, from_attributes=True
            )
            for starts_on, figures in quality.weeks
        ],
        fitting_per_week=quality.fitting_per_week,
        near_misses_left=quality.near_misses_left,
        discard_reasons=[
            DiscardReasonCountRead(reason=reason, offers=offers)
            for reason, offers in quality.discard_reasons
        ],
        sources=[
            SourceQualityRead.model_validate(source, from_attributes=True)
            for source in quality.sources
        ],
    )


@offers_router.get("/{offer_id}", responses=_NOT_FOUND)
async def read_offer(offer_id: UUID, service: Service) -> OfferRead:
    offer = await service.get(offer_id)
    return OfferRead.model_validate(offer, from_attributes=True)


@offers_router.post(
    "/{offer_id}/discard",
    status_code=HTTPStatus.CREATED,
    responses={
        **_NOT_FOUND,
        **_WRONG_STATUS,
        HTTPStatus.UNPROCESSABLE_CONTENT: {
            "model": ValidationProblemRead | ProblemRead,
            "description": "Invalid body (`validation-error`), or the word is not a word of "
            "the title (`word-not-in-title`)",
        },
    },
)
async def discard_offer(offer_id: UUID, discard: DiscardCreate, service: Service) -> OfferRead:
    """Discard a pending offer with its reason; `none` when no other is given."""
    discarded = await service.discard(offer_id, discard.reason, discard.word)
    return OfferRead.model_validate(discarded, from_attributes=True)


@offers_router.delete(
    "/{offer_id}/discard",
    status_code=HTTPStatus.NO_CONTENT,
    responses={**_NOT_FOUND, **_WRONG_STATUS},
)
async def restore_offer(offer_id: UUID, service: Service) -> None:
    """Undo the discard: the offer is pending again."""
    await service.restore(offer_id)


@offers_router.post(
    "/{offer_id}/rightly-filtered",
    status_code=HTTPStatus.CREATED,
    responses={
        **_NOT_FOUND,
        HTTPStatus.CONFLICT: {
            "model": ProblemRead,
            "description": "The offer is not filtered (`offer-not-filtered`)",
        },
    },
)
async def mark_rightly_filtered(offer_id: UUID, service: Service) -> OfferRead:
    """Keep a filtered offer filtered, as reviewed: it is no longer a near miss."""
    marked = await service.mark_rightly_filtered(offer_id)
    return OfferRead.model_validate(marked, from_attributes=True)


@offers_router.delete(
    "/{offer_id}/rightly-filtered",
    status_code=HTTPStatus.NO_CONTENT,
    responses=_NOT_FOUND,
)
async def unmark_rightly_filtered(offer_id: UUID, service: Service) -> None:
    """Undo the mark; nothing changes if the offer is not marked rightly filtered."""
    await service.unmark_rightly_filtered(offer_id)


@offers_router.post(
    "/{offer_id}/promotion",
    status_code=HTTPStatus.CREATED,
    responses={**_NOT_FOUND, **_WRONG_STATUS},
)
async def promote_offer(offer_id: UUID, promotion: PromotionCreate, service: Service) -> OfferRead:
    """Turn a pending offer into an application in `evaluated`.

    The application uses the company with the offer's company name, ignoring case,
    or a new one; the title becomes the role and the offer's URL is kept.
    """
    promoted = await service.promote(offer_id, promotion.channel)
    return OfferRead.model_validate(promoted, from_attributes=True)


# --- Public feeds ---

imports_router = APIRouter(prefix="/job-boards", tags=["inbox"])


def get_feed_import_service(
    session: SessionDep,
    client: Annotated[httpx2.AsyncClient, Depends(get_feed_client)],
) -> FeedImportService:
    # One session for both modules: the offers and the import date are all or nothing.
    return FeedImportService(
        FeedImportRepository(session),
        build_search_profile_service(session),
        build_job_board_service(session),
        FeedReader(client),
    )


FeedService = Annotated[FeedImportService, Depends(get_feed_import_service)]


@imports_router.post(
    "/{job_board_id}/imports",
    status_code=HTTPStatus.CREATED,
    responses={
        HTTPStatus.NOT_FOUND: {"model": ProblemRead, "description": "Job board does not exist"},
        HTTPStatus.CONFLICT: {
            "model": ProblemRead,
            "description": "The job board's import method is `none` "
            "(`job-board-not-imported`) or `email` (`job-board-imported-by-email`)",
        },
        HTTPStatus.TOO_MANY_REQUESTS: {
            "model": ProblemRead,
            "description": "Imported less than 6 hours ago (`feed-cooldown`); "
            "`Retry-After` gives the seconds to wait",
        },
        HTTPStatus.BAD_GATEWAY: {
            "model": ProblemRead,
            "description": "The feed or RSS did not answer or could not be read "
            "(`feed-unavailable`); nothing changed",
        },
    },
)
async def import_job_board(
    job_board_id: UUID, service: FeedService, clock: Annotated[Clock, Depends(get_clock)]
) -> ImportRead:
    """Add every offer of the job board's feed or RSS to the inbox, as pending, with the
    job board as their source; the ones that fit no search profile are filtered. Himalayas
    and the RSS are searched by the titles of every profile; RSS items read
    `Company: Title`.

    Duplicates are skipped; pending imported offers of this job board that left its feed
    or RSS are discarded as expired. A job board can be imported at most once every 6
    hours (each source's terms).
    """
    result = await service.import_job_board(job_board_id, clock.now())
    return ImportRead(
        job_board_id=result.job_board_id,
        found=result.found,
        added=result.added,
        filtered=result.filtered,
        already_in_inbox=result.found - result.added,
        expired=result.expired,
        imported_at=result.imported_at,
    )


# --- ATS companies ---

watched_companies_router = APIRouter(prefix="/watched-companies", tags=["inbox"])


def get_watched_company_service(
    session: SessionDep,
    client: Annotated[httpx2.AsyncClient, Depends(get_feed_client)],
) -> WatchedCompanyService:
    # The ATS boards are read with the feeds' client: same User-Agent and timeout.
    return WatchedCompanyService(
        WatchedCompanyRepository(session),
        build_search_profile_service(session),
        BoardReader(client),
    )


WatchedService = Annotated[WatchedCompanyService, Depends(get_watched_company_service)]

_WATCHED_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    HTTPStatus.NOT_FOUND: {"model": ProblemRead, "description": "Watched company does not exist"}
}


@watched_companies_router.post(
    "",
    status_code=HTTPStatus.CREATED,
    responses={
        HTTPStatus.CONFLICT: {
            "model": ProblemRead,
            "description": "A company with that name, ignoring case, is already watched "
            "(`already-exists`)",
        },
    },
)
async def watch_company(
    company: WatchedCompanyCreate, service: WatchedService
) -> WatchedCompanyRead:
    """Watch a company through the public job board of its ATS."""
    created = await service.create(company)
    return WatchedCompanyRead.model_validate(created, from_attributes=True)


@watched_companies_router.get("")
async def list_watched_companies(service: WatchedService) -> list[WatchedCompanyRead]:
    """Every watched company, by name."""
    return [
        WatchedCompanyRead.model_validate(row, from_attributes=True)
        for row in await service.list_all()
    ]


@watched_companies_router.delete(
    "/{watched_company_id}", status_code=HTTPStatus.NO_CONTENT, responses=_WATCHED_NOT_FOUND
)
async def unwatch_company(watched_company_id: UUID, service: WatchedService) -> None:
    """Stop watching a company. Its offers stay in the inbox, with no watched company."""
    await service.delete(watched_company_id)


@watched_companies_router.post(
    "/{watched_company_id}/imports",
    status_code=HTTPStatus.CREATED,
    responses={
        **_WATCHED_NOT_FOUND,
        HTTPStatus.BAD_GATEWAY: {
            "model": ProblemRead,
            "description": "The ATS did not answer or does not know the board "
            "(`board-unavailable`); nothing changed",
        },
    },
)
async def import_watched_company(
    watched_company_id: UUID, service: WatchedService, clock: Annotated[Clock, Depends(get_clock)]
) -> BoardImportRead:
    """Add every open offer of the company to the inbox, as pending; the ones that fit no
    search profile are filtered.

    Duplicates are skipped; pending offers of this company that left its board are
    discarded as expired. No limit on how often: the ATS boards state none.
    """
    result = await service.import_board(watched_company_id, clock.now())
    return BoardImportRead(
        watched_company_id=result.watched_company_id,
        found=result.found,
        added=result.added,
        filtered=result.filtered,
        already_in_inbox=result.found - result.added,
        expired=result.expired,
        imported_at=result.imported_at,
    )


# --- Email alerts ---

email_alerts_router = APIRouter(prefix="/email-alerts", tags=["inbox"])


def get_email_alert_service(session: SessionDep) -> EmailAlertService:
    return EmailAlertService(
        FeedImportRepository(session),
        build_search_profile_service(session),
        build_job_board_service(session),
    )


@email_alerts_router.post(
    "/imports",
    status_code=HTTPStatus.CREATED,
    responses={
        HTTPStatus.CONFLICT: {
            "model": ProblemRead,
            "description": "No job board imports this email alert "
            "(`email-alert-not-imported`); nothing changed",
        },
        HTTPStatus.UNPROCESSABLE_CONTENT: {
            "model": ProblemRead,
            "description": "Not a supported alert (`unsupported-alert`): only LinkedIn's "
            "job alerts are read",
        },
    },
)
async def import_email_alert(
    email: AlertEmailCreate,
    service: Annotated[EmailAlertService, Depends(get_email_alert_service)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> AlertImportRead:
    """Add every offer of a job alert email to the inbox, as pending, with the job board
    that imports the alert (import method `email`) as their source; the ones that fit no
    search profile are filtered. Any LinkedIn job alert is read, whatever its search.

    Duplicates are skipped. Each offer links to the posting without the email's tracking.
    Offers of alerts never expire and there is no limit: an alert lists only new offers.
    """
    result = await service.import_alert(email.sender, email.text, clock.now())
    return AlertImportRead(
        job_board_id=result.job_board_id,
        found=result.found,
        added=result.added,
        filtered=result.filtered,
        already_in_inbox=result.found - result.added,
        imported_at=result.imported_at,
    )


criteria_changes_router = APIRouter(prefix="/criteria-changes", tags=["inbox"])


def get_criteria_change_service(
    session: SessionDep, offers: Annotated[OfferService, Depends(get_offer_service)]
) -> CriteriaChangeService:
    return CriteriaChangeService(
        CriteriaChangeRepository(session), offers, build_search_profile_service(session)
    )


ChangeService = Annotated[CriteriaChangeService, Depends(get_criteria_change_service)]


@criteria_changes_router.post(
    "",
    status_code=HTTPStatus.CREATED,
    responses={
        HTTPStatus.NOT_FOUND: {
            "model": ProblemRead,
            "description": "The profile or the offer does not exist",
        }
    },
)
async def make_criteria_change(
    change: CriteriaChangeCreate, service: ChangeService
) -> CriteriaChangeRead:
    """Change one rule of a search profile, logged with what it did when applied."""
    made = await service.make(change)
    return CriteriaChangeRead.model_validate(made, from_attributes=True)


@criteria_changes_router.get("")
async def list_criteria_changes(
    page: Annotated[PageParams, Depends(get_page_params)], service: ChangeService
) -> Page[CriteriaChangeRead]:
    """The changes, from the most recent."""
    changes, total = await service.list_page(page)
    return Page(
        items=[CriteriaChangeRead.model_validate(row, from_attributes=True) for row in changes],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@criteria_changes_router.delete(
    "/{change_id}",
    status_code=HTTPStatus.NO_CONTENT,
    responses={
        HTTPStatus.NOT_FOUND: {"model": ProblemRead, "description": "Change does not exist"},
        HTTPStatus.CONFLICT: {
            "model": ProblemRead,
            "description": "A later change edited the same rule (`rule-changed-since`)",
        },
    },
)
async def undo_criteria_change(change_id: UUID, service: ChangeService) -> None:
    """Undo a change: its rule goes back as it was and the change leaves the log."""
    await service.undo(change_id)


suggestions_router = APIRouter(prefix="/criteria-suggestions", tags=["inbox"])


def get_suggestion_service(
    session: SessionDep, offers: Annotated[OfferService, Depends(get_offer_service)]
) -> CriteriaSuggestionService:
    return CriteriaSuggestionService(
        SuggestionRepository(session), offers, build_search_profile_service(session)
    )


SuggestionService = Annotated[CriteriaSuggestionService, Depends(get_suggestion_service)]


@suggestions_router.get("")
async def list_criteria_suggestions(
    page: Annotated[PageParams, Depends(get_page_params)], service: SuggestionService
) -> Page[CriteriaSuggestionRead]:
    """Words to exclude, counted from the discarded and promoted offers or suggested by the
    offer triager; never applied."""
    suggestions = await service.list_all()
    return Page(
        items=[
            CriteriaSuggestionRead.model_validate(suggestion, from_attributes=True)
            for suggestion in suggestions[page.offset : page.offset + page.limit]
        ],
        total=len(suggestions),
        limit=page.limit,
        offset=page.offset,
    )


@suggestions_router.post(
    "/dismissals",
    status_code=HTTPStatus.CREATED,
    responses={
        HTTPStatus.NOT_FOUND: {"model": ProblemRead, "description": "Profile does not exist"}
    },
)
async def dismiss_criteria_suggestion(
    dismissal: DismissalCreate, service: SuggestionService
) -> DismissalRead:
    """ "Not now": the change of that word in that rule is not suggested again for the
    profile. Saying it twice is once."""
    await service.dismiss(dismissal.search_profile_id, dismissal.rule, dismissal.word)
    return DismissalRead(
        search_profile_id=dismissal.search_profile_id, rule=dismissal.rule, word=dismissal.word
    )


router = APIRouter()
router.include_router(suggestions_router)
router.include_router(criteria_changes_router)
router.include_router(offers_router)
router.include_router(imports_router)
router.include_router(email_alerts_router)
router.include_router(watched_companies_router)
