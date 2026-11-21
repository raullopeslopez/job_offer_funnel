import re
from collections.abc import AsyncIterator, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when
from support.clock import FixedClock
from support.triages import said

from funnel.core.clock import get_clock
from funnel.modules.discovery.domain import WorkMode
from funnel.modules.inbox.domain import (
    OfferReaderError,
    OfferText,
    OfferTriagerError,
    Reading,
    TriageAnswer,
    TriageContext,
    TriageReply,
    TriagerSuggestion,
)
from funnel.modules.inbox.router import get_feed_client, get_offer_reader, get_offer_triager

pytestmark = pytest.mark.bdd

scenarios("inbox/near_miss_triages.feature")

OFFERS_URL = "/api/v1/offers"
TRIAGES_URL = f"{OFFERS_URL}/triages"
SUGGESTIONS_URL = "/api/v1/criteria-suggestions"
PROFILES_URL = "/api/v1/search-profiles"
LIST_FIELDS = frozenset({"titles", "keywords", "excluded_keywords"})
# Past the 6 hours a job board waits between imports.
LATER = timedelta(hours=7)

Row = dict[str, str]


@dataclass
class ScenarioState:
    remoteok: list[Row] = field(default_factory=list)
    remoteok_id: str | None = None
    imports: int = 0
    # What the fake triager answers, by company (OK when the scenario says nothing); the
    # exclusions it suggests, with the companies they come from; those it leaves out;
    # whether it fails.
    answers: dict[str, TriageAnswer] = field(default_factory=dict)
    quoting_descriptions: set[str] = field(default_factory=set)
    suggestions: list[tuple[str, str, str, list[str]]] = field(default_factory=list)
    unanswered: set[str] = field(default_factory=set)
    is_failing: bool = False
    has_triager: bool = True
    # The work mode the offer reader reads, by company.
    readings: dict[str, WorkMode] = field(default_factory=dict)
    # What it was asked: the offers and the context of each request.
    requests: list[tuple[list[OfferText], TriageContext]] = field(default_factory=list)
    response: httpx2.Response | None = None

    @property
    def last_response(self) -> httpx2.Response:
        assert self.response is not None, "no request was made in this scenario"
        return self.response

    @property
    def last_request(self) -> tuple[list[OfferText], TriageContext]:
        assert self.requests, "the offer triager was not asked"
        return self.requests[-1]


@pytest.fixture
def state() -> ScenarioState:
    return ScenarioState()


class FakeOfferTriager:
    """Answers what the scenario says; an offer it knows nothing about is OK."""

    batch_size = 5  # Groq's

    def __init__(self, state: ScenarioState) -> None:
        self._state = state

    async def triage(self, offers: Sequence[OfferText], context: TriageContext) -> TriageReply:
        self._state.requests.append((list(offers), context))
        if self._state.is_failing:
            raise OfferTriagerError("the triager is down")
        answers: Mapping[int, TriageAnswer] = {
            number: self._state.answers.get(offer.company, _fits(offer, self._state))
            for number, offer in enumerate(offers)
            if offer.company not in self._state.unanswered
        }
        numbers = {offer.company: number for number, offer in enumerate(offers)}
        suggestions = [
            TriagerSuggestion(profile, word, why, [numbers[c] for c in companies if c in numbers])
            for profile, word, why, companies in self._state.suggestions
        ]
        return TriageReply(answers, suggestions)


def _fits(offer: OfferText, state: ScenarioState) -> TriageAnswer:
    """OK, quoting its description when the scenario says so."""
    quote = offer.description if offer.company in state.quoting_descriptions else None
    return TriageAnswer("ok", "Fits.", quote_yes=quote)


class FakeOfferReader:
    """Reads the work mode the scenario says; a description it knows nothing about says
    nothing."""

    def __init__(self, state: ScenarioState) -> None:
        self._state = state

    batch_size = 5

    async def read(self, offer: OfferText, _location: str | None) -> Reading:
        mode = self._state.readings.get(offer.company)
        # The description is its evidence: a reading is kept only with one.
        return Reading(work_mode=mode, work_mode_evidence=offer.description if mode else None)

    async def read_batch(
        self, questions: Sequence[tuple[OfferText, str | None]]
    ) -> list[Reading | OfferReaderError]:
        return [await self.read(offer, location) for offer, location in questions]


@pytest.fixture(autouse=True)
def fake_sources(client: TestClient, state: ScenarioState) -> Iterator[None]:
    """Remote OK and the offer triager answer from the scenario: tests never reach the
    internet."""

    def answer(_request: httpx2.Request) -> httpx2.Response:
        jobs = [
            {
                "position": r["title"],
                "company": r["company"],
                "description": r["description"],
                "url": r["url"],
                "location": r.get("location"),
            }
            for r in state.remoteok
        ]
        return httpx2.Response(200, json=[{"legal": "Link back to Remote OK."}, *jobs])

    async def fake_client() -> AsyncIterator[httpx2.AsyncClient]:
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(answer)) as fake:
            yield fake

    overrides = cast(FastAPI, client.app).dependency_overrides
    overrides[get_feed_client] = fake_client
    overrides[get_offer_triager] = lambda: FakeOfferTriager(state) if state.has_triager else None
    overrides[get_offer_reader] = lambda: FakeOfferReader(state)
    yield
    overrides.pop(get_feed_client, None)
    overrides.pop(get_offer_triager, None)
    overrides.pop(get_offer_reader, None)
    overrides.pop(get_clock, None)


def _ok(response: httpx2.Response, status: int = 201) -> dict[str, Any]:
    assert response.status_code == status, response.text
    body: dict[str, Any] = response.json() if response.content else {}
    return body


def _rows(datatable: list[list[str]]) -> list[Row]:
    header, *rows = datatable
    return [dict(zip(header, values, strict=True)) for values in rows]


def _offer(client: TestClient, company: str) -> dict[str, Any]:
    items = _ok(client.get(OFFERS_URL, params={"limit": "100"}), 200)["items"]
    offer: dict[str, Any] = next(o for o in items if o["company"] == company)
    return offer


def _profile(client: TestClient, name: str) -> dict[str, Any]:
    items = _ok(client.get(PROFILES_URL, params={"limit": "100"}), 200)["items"]
    profile: dict[str, Any] = next(p for p in items if p["name"] == name)
    return profile


def _suggestions(client: TestClient) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = _ok(client.get(SUGGESTIONS_URL), 200)["items"]
    return items


def _suggestion(client: TestClient, word: str, profile: str) -> dict[str, Any] | None:
    return next(
        (
            s
            for s in _suggestions(client)
            if s["word"].casefold() == word.casefold() and s["search_profile_name"] == profile
        ),
        None,
    )


def _offer_url(client: TestClient, company: str) -> str:
    return f"{OFFERS_URL}/{_offer(client, company)['id']}"


def _import(client: TestClient, state: ScenarioState) -> None:
    # Each import a few hours after the last one, so the job board's wait never stops it.
    clock = FixedClock(datetime.now(UTC) + LATER * state.imports)
    cast(FastAPI, client.app).dependency_overrides[get_clock] = lambda: clock
    state.imports += 1
    _ok(client.post(f"/api/v1/job-boards/{state.remoteok_id}/imports"))


# --- Given ---


@given(parsers.parse('a job board named "Remote OK" imported from the feed "remoteok"'))
def given_remoteok_job_board(client: TestClient, state: ScenarioState) -> None:
    body = {
        "name": "Remote OK",
        "search_url_template": "https://remoteok.com/?q={query}",
        "syntax": "keywords",
        "import_method": "api",
        "feed": "remoteok",
    }
    state.remoteok_id = _ok(client.post("/api/v1/job-boards", json=body))["id"]


@given(parsers.parse('a search profile named "{name}" with:'))
def given_profile(client: TestClient, name: str, datatable: list[list[str]]) -> None:
    body: dict[str, Any] = {"name": name}
    for key, value in datatable:
        is_list = key in LIST_FIELDS or key == "work_modes"
        body[key] = re.split(r"\s*,\s*", value) if is_list else value
    _ok(client.post(PROFILES_URL, json=body))


@given(parsers.parse('the job board "Remote OK" was imported with:'))
def given_imported(client: TestClient, state: ScenarioState, datatable: list[list[str]]) -> None:
    # The feed keeps publishing what it published before: those offers are not expired.
    state.remoteok = [*state.remoteok, *_rows(datatable)]
    _import(client, state)
    if state.readings:
        while _ok(client.post(f"{OFFERS_URL}/readings"))["left"]:
            pass


@given(parsers.parse('the offer reader reads the offer of "{company}" as "{mode}"'))
def given_reader(state: ScenarioState, company: str, mode: str) -> None:
    # Imported offers are read as they come in.
    state.readings[company] = WorkMode(mode)


@given(
    parsers.parse('I discarded an imported offer as "{title}" with the description "{description}"')
)
def given_discarded_imported(
    client: TestClient, state: ScenarioState, title: str, description: str
) -> None:
    url = f"https://remoteok.com/discarded/{len(state.remoteok)}"
    row = {"title": title, "company": "Discarded Co", "description": description, "url": url}
    state.remoteok = [*state.remoteok, row]
    _import(client, state)
    _ok(client.post(f"{_offer_url(client, 'Discarded Co')}/discard", json={}))


@given(
    parsers.re(
        r'the offer triager says the offer of "(?P<company>[^"]+)" is (?P<verdict>OK|KO)'
        r'(?: because "(?P<why>[^"]*)")?(?:, quoting "(?P<quote>[^"]*)")?$'
    )
)
def given_answer(
    state: ScenarioState, company: str, verdict: str, why: str | None, quote: str | None
) -> None:
    state.answers[company] = said(verdict, why or "Why.", quote=quote)


@given(
    parsers.re(
        r"the offer triager says the offers of (?P<companies>.+) are OK, quoting their "
        r"descriptions$"
    )
)
def given_ok_offers(state: ScenarioState, companies: str) -> None:
    state.quoting_descriptions |= set(re.findall(r'"([^"]+)"', companies))


# --- When ---


@given("I triaged the offers")
@when("I triage the offers")
def when_triage(client: TestClient, state: ScenarioState) -> None:
    state.response = client.post(TRIAGES_URL)


@when(parsers.parse('I say "Not now" to the suggestion to stop excluding "{word}" in "{name}"'))
def when_dismiss(client: TestClient, state: ScenarioState, word: str, name: str) -> None:
    body = {
        "search_profile_id": _profile(client, name)["id"],
        "rule": "excluded_keywords",
        "word": word,
    }
    state.response = client.post(f"{SUGGESTIONS_URL}/dismissals", json=body)


@when(parsers.parse('I accept the suggestion carried by the offer of "{company}"'))
def when_accept(client: TestClient, state: ScenarioState, company: str) -> None:
    offer_id = _offer(client, company)["id"]
    suggestion = next(s for s in _suggestions(client) if offer_id in s["offer_ids"])
    body = {
        "search_profile_id": suggestion["search_profile_id"],
        suggestion["rule"]: suggestion["after"],
        "offer_id": offer_id,
    }
    state.response = client.post("/api/v1/criteria-changes", json=body)


# --- Then ---


@then(
    parsers.re(
        r'the offer triager was asked first about the offer of "(?P<first>[^"]+)", then about '
        r"those of (?P<rest>.+)$"
    )
)
def then_asked_in_order(state: ScenarioState, first: str, rest: str) -> None:
    offers, _ = state.last_request
    companies = [offer.company for offer in offers]
    assert len(state.requests) == 1
    assert companies[0] == first
    assert sorted(companies[1:]) == sorted(re.findall(r'"([^"]+)"', rest))


@then(
    parsers.parse(
        'it was told that "{first}" was filtered by "{first_rule}" and "{second}" by '
        '"{second_rule}"'
    )
)
def then_told_rules(
    state: ScenarioState, first: str, first_rule: str, second: str, second_rule: str
) -> None:
    offers, _ = state.last_request
    told = {o.company: o.filtered_by.rule if o.filtered_by else None for o in offers}
    assert (told[first], told[second]) == (first_rule, second_rule)


@then(
    parsers.parse(
        'it was told that "{company}" was filtered by "{rule}" and is published in "{where}"'
    )
)
def then_told_location(state: ScenarioState, company: str, rule: str, where: str) -> None:
    offers, _ = state.last_request
    offer = next(o for o in offers if o.company == company)
    assert offer.filtered_by is not None
    assert (offer.filtered_by.rule, offer.location) == (rule, where)


@then(parsers.parse('the offer triager was not asked about the offer of "{company}"'))
def then_not_asked(state: ScenarioState, company: str) -> None:
    assert all(offer.company != company for offers, _ in state.requests for offer in offers)


@then(parsers.parse('the offer of "{company}" has the verdict "{verdict}" because "{why}"'))
def then_verdict(client: TestClient, company: str, verdict: str, why: str) -> None:
    triage = _offer(client, company)["triage"]
    side = "why_yes" if verdict == "OK" else "why_not"
    assert (triage["verdict"], triage[side]["why"]) == (verdict.lower(), why)


@then(parsers.re(r'the offer of "(?P<company>[^"]+)" has the verdict "(?P<verdict>OK|KO)"$'))
def then_only_verdict(client: TestClient, company: str, verdict: str) -> None:
    assert _offer(client, company)["triage"]["verdict"] == verdict.lower()


@then(parsers.re(r'the offer of "(?P<company>[^"]+)" is (?P<negation>not )?filtered$'))
def then_filtered(client: TestClient, company: str, negation: str | None) -> None:
    assert _offer(client, company)["filtered"] is (negation is None)


@then(
    parsers.parse(
        "the triage says {ko:d} KO among the offers that fit and {ok:d} OK among the near misses"
    )
)
def then_counts(state: ScenarioState, ko: int, ok: int) -> None:
    batch = _ok(state.last_response)
    assert (batch["ko"], batch["to_rescue"]) == (ko, ok)


CHANGES = {"stop excluding": "excluded_keywords", "stop asking for the keyword": "keywords"}


@then(
    parsers.re(
        r"the criteria suggestions include to (?P<change>stop excluding|stop asking for the "
        r"keyword|accept "
        r'the work mode) "(?P<word>[^"]+)" in "(?P<profile>[^"]+)", from the triager because '
        r'"(?P<why>[^"]+)"$'
    ),
    target_fixture="suggestion",
)
def then_includes(
    client: TestClient, change: str, word: str, profile: str, why: str
) -> dict[str, Any]:
    suggestion = _suggestion(client, word, profile)
    assert suggestion is not None, _suggestions(client)
    rule = CHANGES.get(change, "work_modes")
    after = _profile(client, profile)[rule]
    is_removed = change.startswith("stop")
    expected = [w for w in after if w != word] if is_removed else [*after, word]
    assert (suggestion["source"], suggestion["why"]) == ("triager", why)
    assert (suggestion["rule"], suggestion["after"]) == (rule, expected)
    return suggestion


@then(parsers.parse('it comes from the offer of "{company}"'))
def then_comes_from(client: TestClient, suggestion: dict[str, Any], company: str) -> None:
    assert suggestion["offer_ids"] == [_offer(client, company)["id"]]


@then(parsers.parse("it would bring {n:d} offer into Pending"))
def then_brings(suggestion: dict[str, Any], n: int) -> None:
    assert suggestion["preview"]["entering_pending"] == n


@then(parsers.parse('the criteria suggestions include nothing from the offer of "{company}"'))
def then_nothing_from(client: TestClient, company: str) -> None:
    offer_id = _offer(client, company)["id"]
    assert all(offer_id not in s["offer_ids"] for s in _suggestions(client))


@then(parsers.parse('the profile "{name}" has no excluded_keywords'))
def then_no_excluded(client: TestClient, name: str) -> None:
    assert _profile(client, name)["excluded_keywords"] == []


@then(parsers.parse('the latest change came from the offer of "{company}"'))
def then_change_from(client: TestClient, company: str) -> None:
    changes = _ok(client.get("/api/v1/criteria-changes"), 200)["items"]
    assert changes[0]["offer_id"] == _offer(client, company)["id"]
