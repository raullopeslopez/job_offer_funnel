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

from funnel.core.clock import get_clock
from funnel.modules.inbox.domain import (
    OfferText,
    OfferTriagerError,
    TriageAnswer,
    TriageContext,
)
from funnel.modules.inbox.router import get_feed_client, get_offer_triager

pytestmark = pytest.mark.bdd

scenarios("inbox/offer_triages.feature")

OFFERS_URL = "/api/v1/offers"
TRIAGES_URL = f"{OFFERS_URL}/triages"
LIST_FIELDS = frozenset({"titles", "keywords", "excluded_keywords"})
# Past the 6 hours a job board waits between imports.
LATER = timedelta(hours=7)

Row = dict[str, str]


@dataclass
class ScenarioState:
    remoteok: list[Row] = field(default_factory=list)
    remoteok_id: str | None = None
    imports: int = 0
    # What the fake triager answers, by company; those it leaves out; whether it fails.
    answers: dict[str, TriageAnswer] = field(default_factory=dict)
    unanswered: set[str] = field(default_factory=set)
    is_failing: bool = False
    has_triager: bool = True
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
    """Answers what the scenario says; an offer it knows nothing about has nothing to say."""

    def __init__(self, state: ScenarioState) -> None:
        self._state = state

    async def triage(
        self, offers: Sequence[OfferText], context: TriageContext
    ) -> Mapping[int, TriageAnswer]:
        self._state.requests.append((list(offers), context))
        if self._state.is_failing:
            raise OfferTriagerError("the triager is down")
        return {
            number: self._state.answers.get(offer.company, TriageAnswer())
            for number, offer in enumerate(offers)
            if offer.company not in self._state.unanswered
        }


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
    yield
    overrides.pop(get_feed_client, None)
    overrides.pop(get_offer_triager, None)
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
        body[key] = re.split(r"\s*,\s*", value) if key in LIST_FIELDS else value
    _ok(client.post("/api/v1/search-profiles", json=body))


@given(parsers.parse('the job board "Remote OK" was imported with:'))
def given_imported(client: TestClient, state: ScenarioState, datatable: list[list[str]]) -> None:
    state.remoteok = _rows(datatable)
    _import(client, state)


@given(
    parsers.parse('the job board "Remote OK" was imported with {number:d} more offers as "{title}"')
)
def given_more_imported(client: TestClient, state: ScenarioState, number: int, title: str) -> None:
    state.remoteok += [
        {
            "title": title,
            "company": f"Company {index}",
            "description": "Python services.",
            "url": f"https://remoteok.com/more/{index}",
        }
        for index in range(number)
    ]
    _import(client, state)


@given(
    parsers.parse('the job board "Remote OK" was imported again without the offer of "{company}"')
)
def given_imported_again(client: TestClient, state: ScenarioState, company: str) -> None:
    state.remoteok = [row for row in state.remoteok if row["company"] != company]
    _import(client, state)


@given(parsers.parse('an offer for "{company}" as "{title}"'))
def given_offer(client: TestClient, company: str, title: str) -> None:
    body = {"url": "https://jobs.example/hand", "company": company, "title": title}
    _ok(client.post(OFFERS_URL, json=body))


@given(
    parsers.re(r'I discarded the offer of "(?P<company>[^"]+)"(?: because "(?P<reason>[^"]+)")?$')
)
def given_discarded(client: TestClient, company: str, reason: str | None) -> None:
    body = {} if reason is None else {"reason": reason}
    _ok(client.post(f"{_offer_url(client, company)}/discard", json=body))


@given(parsers.parse('I promoted the offer of "{company}"'))
def given_promoted(client: TestClient, company: str) -> None:
    _ok(client.post(f"{_offer_url(client, company)}/promotion", json={}))


@given(
    parsers.parse(
        'the offer triager answers for the offer of "{company}" with the reason "{reason}" '
        'and the evidence "{evidence}"'
    )
)
def given_answer(state: ScenarioState, company: str, reason: str, evidence: str) -> None:
    state.answers[company] = TriageAnswer(reason=reason, evidence=evidence)


@given(parsers.parse('the offer triager does not answer for the offer of "{company}"'))
def given_unanswered(state: ScenarioState, company: str) -> None:
    state.unanswered.add(company)


@given("the offer triager fails")
def given_failing(state: ScenarioState) -> None:
    state.is_failing = True


@given(parsers.re(r"the offer triager is (?P<triager>configured|missing)$"))
def given_triager(state: ScenarioState, triager: str) -> None:
    state.has_triager = triager == "configured"


# --- When ---


@given("I triaged the offers")
@when("I triage the offers")
def when_triage(client: TestClient, state: ScenarioState) -> None:
    state.response = client.post(TRIAGES_URL)


@when("I check whether the triage is available")
def when_check(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(f"{OFFERS_URL}/triager")


# --- Then ---


@then(
    parsers.parse(
        'the offer of "{company}" has a suggested discard because "{reason}" with "{evidence}"'
    )
)
def then_suggested(client: TestClient, company: str, reason: str, evidence: str) -> None:
    expected = {"reason": reason, "evidence": evidence}
    assert _offer(client, company)["suggested_discard"] == expected


@then(parsers.parse('the offer of "{company}" has no suggested discard'))
def then_no_suggestion(client: TestClient, company: str) -> None:
    assert _offer(client, company)["suggested_discard"] is None


@then(parsers.parse('the offer of "{company}" is "{status}"'))
def then_status(client: TestClient, company: str, status: str) -> None:
    assert _offer(client, company)["status"] == status


@then(
    parsers.parse("the triage triaged {triaged:d} offers, failed on {failed:d} and left {left:d}")
)
def then_batch(state: ScenarioState, triaged: int, failed: int, left: int) -> None:
    assert _ok(state.last_response) == {"triaged": triaged, "failed": failed, "left": left}


@then(parsers.re(r"the offer triager was asked once, only about the offers of (?P<companies>.+)$"))
def then_asked(state: ScenarioState, companies: str) -> None:
    offers, _ = state.last_request
    expected = sorted(re.findall(r'"([^"]+)"', companies))
    assert (len(state.requests), sorted(offer.company for offer in offers)) == (1, expected)


@then(parsers.parse('the offer triager was told the profile "{name}" and these decisions:'))
def then_told_decisions(state: ScenarioState, name: str, datatable: list[list[str]]) -> None:
    _, context = state.last_request
    told = sorted(
        (d.title, str(d.status), str(d.reason or ""), d.word or "") for d in context.decisions
    )
    expected = sorted(
        (row["title"], row["decision"], row["reason"], row["word"]) for row in _rows(datatable)
    )
    assert ([terms.name for terms in context.profiles], told) == ([name], expected)


@then("the offer triager was told these mistakes:")
def then_told_mistakes(state: ScenarioState, datatable: list[list[str]]) -> None:
    _, context = state.last_request
    told = sorted(
        (m.title, str(m.mistake).replace("_", " "), str(m.reason or "")) for m in context.mistakes
    )
    expected = sorted((row["title"], row["mistake"], row["reason"]) for row in _rows(datatable))
    assert told == expected


@then(parsers.re(r"it is (?P<availability>available|not available)$"))
def then_available(state: ScenarioState, availability: str) -> None:
    assert _ok(state.last_response, 200) == {"is_available": availability == "available"}


@then("it is rejected because the offer triager is not available")
def then_unavailable(state: ScenarioState) -> None:
    assert state.last_response.status_code == 503, state.last_response.text
    assert state.last_response.json()["type"] == "/problems/offer-triager-unavailable"
