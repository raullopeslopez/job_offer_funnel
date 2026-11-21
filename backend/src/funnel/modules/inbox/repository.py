import re
from collections.abc import Collection, Sequence
from dataclasses import replace
from datetime import datetime
from typing import Any, cast
from uuid import UUID, uuid7

from sqlalchemy import (
    Boolean,
    ColumnElement,
    CursorResult,
    Select,
    String,
    Text,
    and_,
    any_,
    case,
    column,
    delete,
    exists,
    false,
    func,
    literal,
    not_,
    or_,
    select,
    true,
    update,
    values,
)
from sqlalchemy import Uuid as UuidType
from sqlalchemy import (
    cast as sql_cast,
)
from sqlalchemy.dialects.postgresql import ARRAY, array, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import with_expression

from funnel.core.db import flush_checking_unique
from funnel.core.exceptions import AlreadyExistsError
from funnel.core.pagination import PageParams
from funnel.modules.discovery.domain import SearchTerms
from funnel.modules.inbox.domain import (
    COUNTRY_FORMS,
    EXPIRED_REASON,
    LOCATION_SEPARATOR,
    Decision,
    DiscardReason,
    FilterReason,
    FitChange,
    Mistake,
    OfferFilter,
    OfferStatus,
    ProfileMatch,
    ProfileRule,
    QualityOffer,
    Reading,
    Review,
    ReviewMade,
    Rule,
    SuggestedDiscard,
    Triage,
    TriageMistake,
    UnknownJobBoardError,
    UntitledOffer,
    Verdict,
    WordHits,
    country_forms,
    filter_reason,
    near_misses_by_rule,
)
from funnel.modules.inbox.models import (
    JOB_BOARD_FOREIGN_KEY,
    UNIQUE_DUPLICATE_KEY,
    UNIQUE_URL_KEY,
    UNIQUE_WATCHED_NAME_INDEX,
    CriteriaChangeRow,
    DismissedSuggestionRow,
    OfferReadingRow,
    OfferRow,
    TriagerSuggestionRow,
    WatchedCompanyRow,
)


def _read_for(location: str | None) -> ColumnElement[bool]:
    return and_(
        OfferReadingRow.offer_id == OfferRow.id,
        OfferReadingRow.location.is_not_distinct_from(location),
    )


def _contradicted(terms: SearchTerms) -> ColumnElement[bool]:
    """Its reading for the profile's location says something the profile rules out. Only
    what is known counts: an offer not read, or a NULL answer, contradicts nothing."""
    reasons: list[ColumnElement[bool]] = [
        OfferReadingRow.stable.is_(False),
        OfferReadingRow.engineering.is_(False),
    ]
    if terms.work_modes:
        reasons.append(OfferReadingRow.work_mode.not_in(terms.work_modes))
    if terms.location is not None:
        reasons.append(OfferReadingRow.admits_location.is_(False))
    reasons += [_in_stack(excluded) for excluded in terms.excluded_keywords]
    return exists().where(_read_for(terms.location), or_(*reasons))


def _in_stack(word: str) -> ColumnElement[bool]:
    """A name of the reading's main stack has the word as a whole word, ignoring case, as
    domain.in_stack says."""
    pattern = rf"(^|[^[:alnum:]_]){re.escape(word)}($|[^[:alnum:]_])"
    return func.array_to_string(OfferReadingRow.stack, ", ").regexp_match(pattern, flags="i")


def _texts(values: Collection[str]) -> ColumnElement[Any]:
    return sql_cast(array(sorted(values)), ARRAY(Text))


def _among(offer_ids: Collection[UUID]) -> ColumnElement[bool]:
    """One array parameter, however many ids: a parameter per id would hit the driver's
    limit (32,767) with enough near misses."""
    return OfferRow.id == any_(literal(list(offer_ids), ARRAY(UuidType)))


def _ruled_out(location: str | None) -> ColumnElement[bool]:
    """Its published location limits it to other countries than those the profile's
    location names, as domain.rules_out says; never when that location names none."""
    forms = country_forms(location)
    if not forms:
        return false()
    published = func.btrim(func.coalesce(OfferRow.location, ""))
    parts = func.regexp_split_to_array(func.lower(published), LOCATION_SEPARATOR)
    return and_(
        published != "",
        parts.op("<@", return_type=Boolean)(_texts(COUNTRY_FORMS)),
        not_(parts.op("&&", return_type=Boolean)(_texts(forms))),
    )


def _fits(terms: SearchTerms) -> ColumnElement[bool]:
    return and_(_fits_words(terms), not_(_contradicted(terms)), not_(_ruled_out(terms.location)))


def _in_title(word: str) -> ColumnElement[bool]:
    return OfferRow.title.icontains(word, autoescape=True)


def _whole_in_title(word: str) -> ColumnElement[bool]:
    """The word, or its plural in -s or -es, between non-alphanumerics or the title's ends;
    ignoring case. Postgres reads an escaped symbol as itself, so C++ matches literally."""
    pattern = rf"(^|[^[:alnum:]]){re.escape(word)}(e?s)?($|[^[:alnum:]])"
    return OfferRow.title.regexp_match(pattern, flags="i")


def _in_text(word: str) -> ColumnElement[bool]:
    text = OfferRow.title + " " + func.coalesce(OfferRow.description, "")
    return text.icontains(word, autoescape=True)


def _fits_words(terms: SearchTerms) -> ColumnElement[bool]:
    """A title in the offer's title, every keyword in title or description, no exclusion
    in the title as a whole word; ignoring case. Exclusions skip the description: a
    passing mention of an excluded word there would drop good offers."""
    return and_(
        or_(false(), *(_in_title(title) for title in terms.titles)),
        *(_in_text(keyword) for keyword in terms.keywords),
        *(not_(_whole_in_title(excluded)) for excluded in terms.excluded_keywords),
    )


def _word_columns(profiles: Sequence[SearchTerms]) -> list[ColumnElement[bool]]:
    """Whether each word of each profile is in the offer, in the order _word_hits reads."""
    return [
        column
        for terms in profiles
        for column in (
            *(_in_title(title) for title in terms.titles),
            *(_in_text(keyword) for keyword in terms.keywords),
            *(_whole_in_title(excluded) for excluded in terms.excluded_keywords),
        )
    ]


def _word_hits(profiles: Sequence[SearchTerms], flags: Sequence[bool]) -> list[WordHits]:
    found = iter(flags)
    return [
        WordHits(
            titles=[title for title in terms.titles if next(found)],
            keywords=[keyword for keyword in terms.keywords if next(found)],
            excluded=[excluded for excluded in terms.excluded_keywords if next(found)],
        )
        for terms in profiles
    ]


def _reading(row: OfferReadingRow) -> Reading:
    return Reading(
        work_mode=row.work_mode,
        work_mode_evidence=row.work_mode_evidence,
        admits_location=row.admits_location,
        admits_location_evidence=row.admits_location_evidence,
        stable=row.stable,
        stable_evidence=row.stable_evidence,
        engineering=row.engineering,
        engineering_evidence=row.engineering_evidence,
        stack=tuple(row.stack),
        stack_evidence=row.stack_evidence,
    )


# Only pending imported offers have a filter reason.
_HAS_REASON = and_(OfferRow.status == OfferStatus.PENDING, OfferRow.description.is_not(None))


def _fits_any(profiles: Sequence[SearchTerms]) -> ColumnElement[bool]:
    return or_(false(), *(_fits(terms) for terms in profiles))


def filtered(profiles: Sequence[SearchTerms]) -> ColumnElement[bool]:
    """Pending, imported (only those have a description) and fitting no profile."""
    return and_(
        OfferRow.status == OfferStatus.PENDING,
        OfferRow.description.is_not(None),
        not_(_fits_any(profiles)),
    )


def _to_decide(profiles: Sequence[SearchTerms]) -> ColumnElement[bool]:
    """Pending and not filtered: the offers that have variants."""
    return and_(OfferRow.status == OfferStatus.PENDING, not_(filtered(profiles)))


def _variants(profiles: Sequence[SearchTerms]) -> ColumnElement[int]:
    """How many offers to decide share its variant key, itself included; 1 for the others."""
    counts = (
        select(OfferRow.variant_key.label("variant_key"), func.count().label("offers"))
        .where(_to_decide(profiles))
        .group_by(OfferRow.variant_key)
        .subquery()
    )
    shared = (
        select(counts.c.offers)
        .where(counts.c.variant_key == OfferRow.variant_key)
        .scalar_subquery()
    )
    return case((_to_decide(profiles), shared), else_=1)


def _variants_together(
    profiles: Sequence[SearchTerms], groups: Sequence[ColumnElement[Any]]
) -> tuple[ColumnElement[Any], ...]:
    """The order that puts each offer where the most recent of its variants in the same
    group goes. Only the offers to decide have variants: the others go on their own."""
    variant = case(
        (_to_decide(profiles), OfferRow.variant_key), else_=sql_cast(OfferRow.id, String)
    )
    variants = (*groups, variant)
    return (
        func.first_value(OfferRow.created_at)
        .over(partition_by=variants, order_by=_MOST_RECENT)
        .desc(),
        func.first_value(OfferRow.id).over(partition_by=variants, order_by=_MOST_RECENT).desc(),
    )


def _select_offers(profiles: Sequence[SearchTerms]) -> Select[OfferRow]:
    # populate_existing: rows already in the session get `filtered` and `variants` computed
    # again.
    return (
        select(OfferRow)
        .options(
            with_expression(OfferRow.filtered, filtered(profiles)),
            with_expression(OfferRow.variants, _variants(profiles)),
        )
        .execution_options(populate_existing=True)
    )


class OfferRepository:
    """Never commits: the request session does. Every read needs the current search
    profiles, which decide whether each offer is filtered."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, offer: OfferRow, profiles: Sequence[SearchTerms]) -> OfferRow:
        # Read before flushing: after a failed flush the row cannot be loaded any more.
        duplicate = f"An offer for {offer.company} as {offer.title} already exists"
        same_url = f"An offer at {offer.url} already exists"
        self._session.add(offer)
        try:
            await self._session.flush()
        except IntegrityError as error:
            if UNIQUE_DUPLICATE_KEY in str(error.orig):
                raise AlreadyExistsError(duplicate) from error
            if UNIQUE_URL_KEY in str(error.orig):
                raise AlreadyExistsError(same_url) from error
            if JOB_BOARD_FOREIGN_KEY in str(error.orig):
                raise UnknownJobBoardError("The job board does not exist") from error
            raise
        return await self._reload(offer, profiles)

    async def get(self, offer_id: UUID, profiles: Sequence[SearchTerms]) -> OfferRow | None:
        found: OfferRow | None = await self._session.scalar(
            _select_offers(profiles).where(OfferRow.id == offer_id)
        )
        if found is not None:
            await self._set_reasons([found], profiles)
        return found

    async def all_reasons(self, profiles: Sequence[SearchTerms]) -> list[FilterReason]:
        return list((await self._reasons(true(), profiles)).values())

    async def _set_reasons(
        self, offers: Sequence[OfferRow], profiles: Sequence[SearchTerms]
    ) -> None:
        reasons = await self._reasons(OfferRow.id.in_([offer.id for offer in offers]), profiles)
        for offer in offers:
            offer.filter_reason = reasons.get(offer.id)

    async def _reasons(
        self, condition: ColumnElement[bool], profiles: Sequence[SearchTerms]
    ) -> dict[UUID, FilterReason]:
        """The filter reason of each pending imported offer the condition selects. The
        database finds the words; the domain decides the rules and the reference profile."""
        words = await self._session.execute(
            select(
                OfferRow.id,
                OfferRow.description != "",
                OfferRow.review.is_not_distinct_from(Review.RIGHTLY_FILTERED),
                OfferRow.location,
                *_word_columns(profiles),
            ).where(_HAS_REASON, condition)
        )
        readings = {
            (row.offer_id, row.location): _reading(row)
            for row in await self._session.scalars(
                select(OfferReadingRow)
                .join(OfferRow, OfferRow.id == OfferReadingRow.offer_id)
                .where(_HAS_REASON, condition)
            )
        }
        return {
            offer_id: replace(
                filter_reason(
                    [
                        ProfileMatch(
                            terms, hits, readings.get((offer_id, terms.location)), location
                        )
                        for terms, hits in zip(profiles, _word_hits(profiles, flags), strict=True)
                    ],
                    has_description=has_description,
                ),
                is_rightly_filtered=is_rightly_filtered,
            )
            for offer_id, has_description, is_rightly_filtered, location, *flags in words
        }

    async def without_a_title_of(
        self, terms: SearchTerms, profiles: Sequence[SearchTerms]
    ) -> list[UntitledOffer]:
        """The filtered offers with none of the profile's titles, the oldest first."""
        rows = await self._session.execute(
            select(
                OfferRow.title,
                and_(true(), *(_in_text(keyword) for keyword in terms.keywords)),
                not_(_contradicted(terms)),
            )
            .where(
                filtered(profiles),
                not_(or_(false(), *(_in_title(title) for title in terms.titles))),
            )
            .order_by(OfferRow.created_at, OfferRow.id)
        )
        return [UntitledOffer(*row) for row in rows]

    async def fit_changes(
        self, current: Sequence[SearchTerms], changed: Sequence[SearchTerms]
    ) -> list[FitChange]:
        """The imported offers, not expired, grouped by status and whether they fit each set
        of profiles, with the same rules that filter the pending ones."""
        fits_now = _fits_any(current).label("fits_now")
        fits_after = _fits_any(changed).label("fits_after")
        rows = await self._session.execute(
            select(OfferRow.status, fits_now, fits_after, func.count())
            .where(
                OfferRow.description.is_not(None),
                OfferRow.discard_reason.is_distinct_from(EXPIRED_REASON),
            )
            .group_by(OfferRow.status, fits_now, fits_after)
        )
        return [FitChange(*row) for row in rows]

    async def added_since(
        self, since: datetime, profiles: Sequence[SearchTerms]
    ) -> list[tuple[QualityOffer, UUID | None]]:
        """The offers added since then, as the quality reads them, with their application."""
        rows = await self._session.execute(
            select(
                OfferRow.created_at,
                OfferRow.status,
                OfferRow.description.is_not(None),
                _fits_any(profiles),
                func.coalesce(OfferRow.job_board_name, OfferRow.watched_company_name),
                OfferRow.discard_reason,
                OfferRow.review,
                OfferRow.review_rules,
                OfferRow.verdict,
                OfferRow.suggested_discard_reason,
                OfferRow.application_id,
            ).where(OfferRow.created_at >= since)
        )
        zone = since.tzinfo
        return [
            (
                QualityOffer(
                    added_on=created_at.astimezone(zone).date(),
                    status=status,
                    is_imported=is_imported,
                    fits=fits,
                    source=source,
                    discard_reason=discard_reason,
                    review=review,
                    review_rules=[Rule(rule) for rule in review_rules],
                    verdict=verdict,
                    suggested_discard=suggested_discard,
                ),
                application_id,
            )
            for (
                created_at,
                status,
                is_imported,
                fits,
                source,
                discard_reason,
                review,
                review_rules,
                verdict,
                suggested_discard,
                application_id,
            ) in rows
        ]

    async def all_reviews(self) -> list[ReviewMade]:
        rows = await self._session.execute(
            select(OfferRow.review, OfferRow.review_rules).where(OfferRow.review.is_not(None))
        )
        return [
            # The query leaves out the offers without a review.
            ReviewMade(cast(Review, review), [Rule(rule) for rule in rules])
            for review, rules in rows
        ]

    async def save(self, offer: OfferRow, profiles: Sequence[SearchTerms]) -> OfferRow:
        await self._session.flush()
        return await self._reload(offer, profiles)

    async def _reload(self, offer: OfferRow, profiles: Sequence[SearchTerms]) -> OfferRow:
        # Loads what the database computes (created_at, job_board_name, filtered) here, not
        # lazily outside async code.
        reloaded = await self.get(offer.id, profiles)
        assert reloaded is not None
        return reloaded

    async def list_page(
        self, offer_filter: OfferFilter, page: PageParams, profiles: Sequence[SearchTerms]
    ) -> tuple[list[OfferRow], int]:
        conditions = await self._conditions(offer_filter, profiles)
        rows = list(
            await self._session.scalars(
                _select_offers(profiles)
                .where(*conditions)
                .order_by(*_order(offer_filter, profiles))
                .limit(page.limit)
                .offset(page.offset)
            )
        )
        await self._set_reasons(rows, profiles)
        total = await self._session.scalar(
            select(func.count()).select_from(OfferRow).where(*conditions)
        )
        return rows, total or 0

    async def near_miss_groups(
        self, profiles: Sequence[SearchTerms], limit: int
    ) -> list[tuple[Rule, int, list[OfferRow]]]:
        """Each rule with near misses, how many fail it and its most recent ones, up to the
        limit; the filter reasons are worked out once for all of them."""
        reasons = await self._reasons(true(), profiles)
        groups = []
        for rule, offer_ids in near_misses_by_rule(reasons).items():
            rows = list(
                await self._session.scalars(
                    _select_offers(profiles)
                    .where(_among(offer_ids))
                    .order_by(*_MOST_RECENT)
                    .limit(limit)
                )
            )
            for row in rows:
                row.filter_reason = reasons[row.id]
            groups.append((rule, len(offer_ids), rows))
        return groups

    async def _conditions(
        self, offer_filter: OfferFilter, profiles: Sequence[SearchTerms]
    ) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = []
        if offer_filter.status is not None:
            conditions.append(OfferRow.status == offer_filter.status)
        if offer_filter.is_filtered is not None:
            condition = filtered(profiles)
            conditions.append(condition if offer_filter.is_filtered else not_(condition))
        if offer_filter.job_board_id is not None:
            conditions.append(OfferRow.job_board_id == offer_filter.job_board_id)
        if text := (offer_filter.matching_company_or_title or "").strip():
            conditions.append(
                or_(
                    OfferRow.company.icontains(text, autoescape=True),
                    OfferRow.title.icontains(text, autoescape=True),
                )
            )
        if offer_filter.is_near_miss is None and offer_filter.failed_rule is None:
            return conditions
        # Near misses and failed rules are decided by the domain, so they filter by id.
        reasons = await self._reasons(true(), profiles)
        if offer_filter.is_near_miss is not None:
            near_misses = [offer_id for offer_id, reason in reasons.items() if reason.near_miss]
            in_near_misses = _among(near_misses)
            conditions.append(in_near_misses if offer_filter.is_near_miss else not_(in_near_misses))
        if offer_filter.failed_rule is not None:
            failing = [
                offer_id
                for offer_id, reason in reasons.items()
                if offer_filter.failed_rule in reason.failed
            ]
            conditions.append(_among(failing))
        return conditions


class CriteriaChangeRepository:
    """The log of criteria changes. Never commits: the request session does."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, change: CriteriaChangeRow) -> CriteriaChangeRow:
        self._session.add(change)
        await self._session.flush()
        await self._session.refresh(change)  # loads created_at and the profile's name
        return change

    async def get(self, change_id: UUID) -> CriteriaChangeRow | None:
        return await self._session.get(CriteriaChangeRow, change_id)

    async def is_changed_since(self, change: CriteriaChangeRow) -> bool:
        """Whether a later change edited the same rule of the same profile."""
        later = await self._session.scalar(
            select(
                exists().where(
                    CriteriaChangeRow.search_profile_id == change.search_profile_id,
                    CriteriaChangeRow.rule == change.rule,
                    CriteriaChangeRow.id > change.id,
                )
            )
        )
        return bool(later)

    async def delete(self, change: CriteriaChangeRow) -> None:
        await self._session.delete(change)
        await self._session.flush()

    async def list_page(self, page: PageParams) -> tuple[list[CriteriaChangeRow], int]:
        # uuid7 ids follow the order the changes were made.
        rows = await self._session.scalars(
            select(CriteriaChangeRow)
            .order_by(CriteriaChangeRow.id.desc())
            .limit(page.limit)
            .offset(page.offset)
        )
        total = await self._session.scalar(select(func.count()).select_from(CriteriaChangeRow))
        return list(rows), total or 0


class SuggestionRepository:
    """What the suggestions count, and the ones dismissed. Never commits."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def discarded_titles(self) -> list[tuple[UUID, str]]:
        """The imported offers the user discarded: expired ones were discarded by imports."""
        rows = await self._session.execute(
            select(OfferRow.id, OfferRow.title).where(
                OfferRow.status == OfferStatus.DISCARDED,
                OfferRow.description.is_not(None),
                OfferRow.discard_reason.is_distinct_from(EXPIRED_REASON),
            )
        )
        return [(offer_id, title) for offer_id, title in rows]

    async def promoted_titles(self) -> list[str]:
        rows = await self._session.scalars(
            select(OfferRow.title).where(OfferRow.status == OfferStatus.PROMOTED)
        )
        return list(rows)

    async def dismissed(self) -> set[tuple[UUID, ProfileRule, str]]:
        """Each profile, rule and word dismissed, the word in lower case."""
        rows = await self._session.execute(
            select(
                DismissedSuggestionRow.search_profile_id,
                DismissedSuggestionRow.rule,
                func.lower(DismissedSuggestionRow.word),
            )
        )
        return {(profile_id, rule, word) for profile_id, rule, word in rows}

    async def triager_suggestions(self) -> list[TriagerSuggestionRow]:
        rows = await self._session.scalars(
            select(TriagerSuggestionRow).order_by(TriagerSuggestionRow.created_at)
        )
        return list(rows)

    async def keep_triager_suggestion(  # noqa: PLR0913, PLR0917  # the parts of a suggestion
        self,
        profile_id: UUID,
        rule: ProfileRule,
        word: str,
        why: str,
        offer_ids: Sequence[UUID],
    ) -> None:
        """Once per profile, rule and word, ignoring case: suggested again, it takes the new
        why and adds the offers it comes from."""
        kept = await self._session.scalar(
            select(TriagerSuggestionRow).where(
                TriagerSuggestionRow.search_profile_id == profile_id,
                TriagerSuggestionRow.rule == rule,
                func.lower(TriagerSuggestionRow.word) == word.casefold(),
            )
        )
        if kept is None:
            self._session.add(
                TriagerSuggestionRow(
                    search_profile_id=profile_id,
                    rule=rule,
                    word=word,
                    why=why,
                    offer_ids=list(offer_ids),
                )
            )
        else:
            kept.why = why
            kept.offer_ids = list(dict.fromkeys([*kept.offer_ids, *offer_ids]))
        await self._session.flush()

    async def dismiss(self, profile_id: UUID, rule: ProfileRule, word: str) -> None:
        # Once per profile, rule and word: a second "Not now" changes nothing.
        await self._session.execute(
            insert(DismissedSuggestionRow)
            .values(id=uuid7(), search_profile_id=profile_id, rule=rule, word=word)
            .on_conflict_do_nothing()
        )


class ReadingRepository:
    """What the offers' descriptions say. Never commits: the request session does."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_unread(
        self, profiles: Sequence[SearchTerms], limit: int
    ) -> tuple[list[tuple[OfferRow, str | None]], int]:
        """The oldest readings still to be made, each an offer and a location, and how many
        there are in all. An offer is read for the location of each profile it fits by its
        words, if it is pending and has a description."""
        unread: list[tuple[OfferRow, str | None]] = []
        total = 0
        for location in dict.fromkeys(terms.location for terms in profiles):
            words = [_fits_words(terms) for terms in profiles if terms.location == location]
            conditions = (
                OfferRow.status == OfferStatus.PENDING,
                func.coalesce(OfferRow.description, "") != "",
                or_(*words),
                not_(_ruled_out(location)),
                not_(exists().where(_read_for(location))),
            )
            count = await self._session.scalar(
                select(func.count()).select_from(OfferRow).where(*conditions)
            )
            total += count or 0
            offers = await self._session.scalars(
                select(OfferRow)
                .where(*conditions)
                .order_by(OfferRow.created_at, OfferRow.id)
                .limit(limit - len(unread))
            )
            unread += [(offer, location) for offer in offers]
        return unread, total

    async def add(self, offer_id: UUID, location: str | None, reading: Reading) -> None:
        self._session.add(
            OfferReadingRow(
                offer_id=offer_id,
                location=location,
                work_mode=reading.work_mode,
                work_mode_evidence=reading.work_mode_evidence,
                admits_location=reading.admits_location,
                admits_location_evidence=reading.admits_location_evidence,
                stable=reading.stable,
                stable_evidence=reading.stable_evidence,
                engineering=reading.engineering,
                engineering_evidence=reading.engineering_evidence,
                stack=list(reading.stack),
                stack_evidence=reading.stack_evidence,
            )
        )
        await self._session.flush()


_DECIDED_BY_USER = and_(
    OfferRow.description.is_not(None), OfferRow.discard_reason.is_distinct_from(EXPIRED_REASON)
)
_MOST_RECENT = (OfferRow.created_at.desc(), OfferRow.id.desc())
# OK, then no verdict, then KO by the reason of their suggested discard, in the order of
# the list, and those with no suggested discard last.
_SUGGESTED_ORDER = (
    DiscardReason.TITLE_WORD,
    DiscardReason.STACK,
    DiscardReason.LOCATION,
    DiscardReason.CONTRACT,
    DiscardReason.COMPANY,
)
_BY_VERDICT = (
    case((OfferRow.verdict == Verdict.OK, 0), (OfferRow.verdict.is_(None), 1), else_=2),
    case(
        {reason: rank for rank, reason in enumerate(_SUGGESTED_ORDER)},
        value=OfferRow.suggested_discard_reason,
        else_=len(_SUGGESTED_ORDER),
    ),
)


def _order(
    offer_filter: OfferFilter, profiles: Sequence[SearchTerms]
) -> tuple[ColumnElement[Any], ...]:
    groups = _BY_VERDICT if offer_filter.is_by_verdict else ()
    together = _variants_together(profiles, groups) if offer_filter.has_variants_together else ()
    return (*groups, *together, *_MOST_RECENT)


class TriageRepository:
    """What the offer triager is given and what it suggested. Never commits."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_untriaged(
        self, profiles: Sequence[SearchTerms], limit: int
    ) -> tuple[list[OfferRow], int]:
        """The most recent pending imported offers that fit a profile and have no verdict yet,
        and how many there are in all."""
        conditions = (
            OfferRow.status == OfferStatus.PENDING,
            func.coalesce(OfferRow.description, "") != "",
            _fits_any(profiles),
            OfferRow.verdict.is_(None),
        )
        total = await self._session.scalar(
            select(func.count()).select_from(OfferRow).where(*conditions)
        )
        offers = await self._session.scalars(
            select(OfferRow).where(*conditions).order_by(*_MOST_RECENT).limit(limit)
        )
        return list(offers), total or 0

    async def decisions(self, limit: int) -> list[Decision]:
        """The last promoted and the last discarded imported offers, expired ones left out."""
        decisions: list[Decision] = []
        for status in (OfferStatus.PROMOTED, OfferStatus.DISCARDED):
            rows = await self._session.execute(
                select(OfferRow.title, OfferRow.discard_reason, OfferRow.discard_word)
                .where(OfferRow.status == status, _DECIDED_BY_USER)
                .order_by(*_MOST_RECENT)
                .limit(limit)
            )
            decisions += [Decision(title, status, reason, word) for title, reason, word in rows]
        return decisions

    async def mistakes(self, limit: int) -> list[TriageMistake]:
        """The last suggested discards the user promoted, and the last offers marked OK
        that the user discarded."""
        rejected = await self._session.execute(
            select(OfferRow.title, OfferRow.suggested_discard_reason)
            .where(
                OfferRow.status == OfferStatus.PROMOTED,
                OfferRow.suggested_discard_reason.is_not(None),
            )
            .order_by(*_MOST_RECENT)
            .limit(limit)
        )
        missed = await self._session.scalars(
            select(OfferRow.title)
            .where(
                OfferRow.status == OfferStatus.DISCARDED,
                _DECIDED_BY_USER,
                OfferRow.verdict == Verdict.OK,
            )
            .order_by(*_MOST_RECENT)
            .limit(limit)
        )
        return [
            *(
                TriageMistake(title, Mistake.REJECTED_SUGGESTION, reason)
                for title, reason in rejected
            ),
            *(TriageMistake(title, Mistake.MISSED_DISCARD) for title in missed),
        ]

    async def save(
        self, offer: OfferRow, triage: Triage, suggestion: SuggestedDiscard | None
    ) -> None:
        offer.triaged_at = func.now()
        offer.verdict = triage.verdict
        offer.why_yes = None if triage.why_yes is None else triage.why_yes.why
        offer.why_yes_quote = None if triage.why_yes is None else triage.why_yes.quote
        offer.why_not = None if triage.why_not is None else triage.why_not.why
        offer.why_not_quote = None if triage.why_not is None else triage.why_not.quote
        offer.confidence = triage.confidence
        offer.suggested_discard_reason = None if suggestion is None else suggestion.reason
        offer.suggested_discard_evidence = None if suggestion is None else suggestion.evidence
        await self._session.flush()


class FeedImportRepository:
    """Offers coming from feeds.

    Never commits: the request session does.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_new(self, offers: Sequence[OfferRow]) -> list[UUID]:
        """Insert the offers that are not duplicates; return the ids of those inserted.

        ON CONFLICT DO NOTHING keeps the UNIQUE constraints (company and title, URL) as the
        judges of duplicates without aborting the transaction, as a failed flush would.
        """
        if not offers:
            return []
        # Every row must have the same keys in a multi-row VALUES: only the columns the
        # database fills itself are left out when unset.
        values = [
            {
                column.key: getattr(offer, column.key)
                for column in OfferRow.__table__.columns
                if column.server_default is None or getattr(offer, column.key) is not None
            }
            | {"id": offer.id or uuid7()}
            for offer in offers
        ]
        inserted = await self._session.scalars(
            insert(OfferRow).values(values).on_conflict_do_nothing().returning(OfferRow.id)
        )
        added = list(inserted.all())
        await self._fill_locations([offer for offer in offers if offer.location is not None])
        return added

    async def _fill_locations(self, offers: Sequence[OfferRow]) -> None:
        """Give the offers already in the inbox without a location (imported before
        locations were kept) the one their source publishes now. A pending one loses its
        readings, so that it is read again with it."""
        if not offers:
            return
        published = values(
            column("duplicate_key", String),
            column("url_key", String),
            column("location", String),
            name="published",
        ).data([(offer.duplicate_key, offer.url_key, offer.location) for offer in offers])
        filled = await self._session.execute(
            update(OfferRow)
            .where(
                OfferRow.location.is_(None),
                or_(
                    OfferRow.duplicate_key == published.c.duplicate_key,
                    OfferRow.url_key == published.c.url_key,
                ),
            )
            .values(location=published.c.location)
            .returning(OfferRow.id, OfferRow.status)
        )
        pending = [offer_id for offer_id, status in filled if status is OfferStatus.PENDING]
        if pending:
            await self._session.execute(
                delete(OfferReadingRow).where(OfferReadingRow.offer_id.in_(pending))
            )

    async def count_filtered(
        self, offer_ids: Collection[UUID], profiles: Sequence[SearchTerms]
    ) -> int:
        if not offer_ids:
            return 0
        total = await self._session.scalar(
            select(func.count())
            .select_from(OfferRow)
            .where(OfferRow.id.in_(offer_ids), filtered(profiles))
        )
        return total or 0

    async def expire_missing(self, job_board_id: UUID, published_urls: Collection[str]) -> int:
        """Discard as expired the pending offers imported from a job board that its feed no
        longer publishes. Those added by hand (no description) stay."""
        source = and_(OfferRow.job_board_id == job_board_id, OfferRow.description.is_not(None))
        return await self._expire(source, published_urls)

    async def expire_missing_from_board(
        self, watched_company_id: UUID, published_urls: Collection[str]
    ) -> int:
        """Discard as expired the pending offers of a watched company that left its board."""
        return await self._expire(OfferRow.watched_company_id == watched_company_id, published_urls)

    async def _expire(self, source: ColumnElement[bool], published_urls: Collection[str]) -> int:
        result = await self._session.execute(
            update(OfferRow)
            .where(
                source,
                OfferRow.status == OfferStatus.PENDING,
                OfferRow.url.not_in(published_urls),
            )
            .values(status=OfferStatus.DISCARDED, discard_reason=EXPIRED_REASON)
        )
        return cast(CursorResult[Any], result).rowcount


class WatchedCompanyRepository:
    """Watched companies and the offers imported from their boards.

    Never commits: the request session does.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        # Offers from a board are stored like those from a feed.
        self._offers = FeedImportRepository(session)

    async def add_new_offers(self, offers: Sequence[OfferRow]) -> list[UUID]:
        return await self._offers.add_new(offers)

    async def count_filtered(
        self, offer_ids: Collection[UUID], profiles: Sequence[SearchTerms]
    ) -> int:
        return await self._offers.count_filtered(offer_ids, profiles)

    async def expire_missing_offers(self, company_id: UUID, published_urls: Collection[str]) -> int:
        return await self._offers.expire_missing_from_board(company_id, published_urls)

    async def add(self, company: WatchedCompanyRow) -> WatchedCompanyRow:
        detail = f"The company {company.name} is already watched"
        self._session.add(company)
        await flush_checking_unique(self._session, UNIQUE_WATCHED_NAME_INDEX, detail)
        await self._session.refresh(company)  # loads created_at
        return company

    async def get(self, company_id: UUID) -> WatchedCompanyRow | None:
        return await self._session.get(WatchedCompanyRow, company_id)

    async def list_all(self) -> list[WatchedCompanyRow]:
        rows = await self._session.scalars(
            select(WatchedCompanyRow).order_by(
                func.lower(WatchedCompanyRow.name), WatchedCompanyRow.id
            )
        )
        return list(rows)

    async def delete(self, company: WatchedCompanyRow) -> None:
        await self._session.delete(company)
        await self._session.flush()
