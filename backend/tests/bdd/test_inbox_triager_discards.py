import re
from collections.abc import AsyncIterator, Iterator, Sequence
from dataclasses import dataclass, field, replace
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
from funnel.modules.inbox.domain import OfferText, TriageAnswer, TriageContext, TriageReply
from funnel.modules.inbox.router import get_feed_client, get_offer_triager

pytestmark = pytest.mark.bdd

scenarios("inbox/triager_discards.feature")

OFFERS_URL = "/api/v1/offers"
TRIAGES_URL = f"{OFFERS_URL}/triages"
TRIAGER_DISCARDS_URL = f"{OFFERS_URL}/triager-discards"
LIST_FIELDS = frozenset({"titles", "keywords", "excluded_keywords"})
# Past the 6 hours a job board waits between imports.
LATER = timedelta(hours=7)

Row = dict[str, str]


@dataclass
class ScenarioState:
    remoteok: list[Row] = field(default_factory=list)
    remoteok_id: str | None = None
    imports: int = 0
    # What the fake triager answers, by company: it leaves the others untriaged.
    answers: dict[str, TriageAnswer] = field(default_factory=dict)
    is_triager_missing: bool = False
    contexts: list[TriageContext] = field(default_factory=list)
    response: httpx2.Response | None = None

    @property
    def last_response(self) -> httpx2.Response:
        assert self.response is not None, "no request was made in this scenario"
        return self.response


@pytest.fixture
def state() -> ScenarioState:
    return ScenarioState()


class FakeOfferTriager:
    """Answers only for the companies the scenario gives a verdict."""

    batch_size = 5  # Groq's

    def __init__(self, state: ScenarioState) -> None:
        self._state = state

    async def triage(self, offers: Sequence[OfferText], context: TriageContext) -> TriageReply:
        self._state.contexts.append(context)
        answers = {
            number: self._state.answers[offer.company]
            for number, offer in enumerate(offers)
            if offer.company in self._state.answers
        }
        return TriageReply(answers, [])


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
    overrides[get_offer_triager] = lambda: (
        None if state.is_triager_missing else FakeOfferTriager(state)
    )
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


def _profile_id(client: TestClient, name: str) -> str:
    items = _ok(client.get("/api/v1/search-profiles", params={"limit": "100"}), 200)["items"]
    profile_id: str = next(p["id"] for p in items if p["name"] == name)
    return profile_id


def _verdict(  # noqa: PLR0913, PLR0917  # one per part of a verdict
    client: TestClient,
    state: ScenarioState,
    company: str,
    verdict: str,
    confidence: str,
    reason: str | None,
    evidence: str | None,
) -> None:
    answer = said(verdict, "Why.", reason=reason, evidence=evidence)
    state.answers[company] = replace(answer, confidence=confidence)
    _ok(client.post(TRIAGES_URL))


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
    state.remoteok = [*state.remoteok, *_rows(datatable)]
    clock = FixedClock(datetime.now(UTC) + LATER * state.imports)
    cast(FastAPI, client.app).dependency_overrides[get_clock] = lambda: clock
    state.imports += 1
    _ok(client.post(f"/api/v1/job-boards/{state.remoteok_id}/imports"))


@given("these verdicts:")
def given_verdicts(client: TestClient, state: ScenarioState, datatable: list[list[str]]) -> None:
    # A suggested discard comes with valid evidence: the description of the offer.
    descriptions = {row["company"]: row["description"] for row in state.remoteok}
    for row in _rows(datatable):
        reason = row["suggested discard"] or None
        evidence = None if reason is None else descriptions[row["company"]]
        _verdict(client, state, row["company"], row["verdict"], row["confidence"], reason, evidence)


@given(
    parsers.re(
        r'the offer of "(?P<company>[^"]+)" has the verdict (?P<verdict>OK|KO) with '
        r"(?P<confidence>low|medium|high) confidence"
        r'(?:, with a suggested discard because "(?P<reason>[^"]+)" with "(?P<evidence>[^"]+)")?$'
    )
)
def given_verdict(  # noqa: PLR0913, PLR0917  # one per part of the step
    client: TestClient,
    state: ScenarioState,
    company: str,
    verdict: str,
    confidence: str,
    reason: str | None,
    evidence: str | None,
) -> None:
    _verdict(client, state, company, verdict, confidence, reason, evidence)


@given("the offer triager is missing")
def given_triager_missing(state: ScenarioState) -> None:
    state.is_triager_missing = True


@given("I let the triager discard")
def given_triager_discarded(client: TestClient) -> None:
    _ok(client.post(TRIAGER_DISCARDS_URL))


@given(parsers.parse('I restored the offer of "{company}"'))
def given_restored(client: TestClient, company: str) -> None:
    _ok(client.delete(f"{_offer_url(client, company)}/discard"), 204)


@given(
    parsers.parse('I discarded the offer of "{company}" because "{reason}" with the word "{word}"')
)
def given_discarded_with_word(client: TestClient, company: str, reason: str, word: str) -> None:
    body = {"reason": reason, "word": word}
    _ok(client.post(f"{_offer_url(client, company)}/discard", json=body), 200)


# --- When ---


@when("I let the triager discard")
def when_triager_discards(client: TestClient, state: ScenarioState) -> None:
    state.response = client.post(TRIAGER_DISCARDS_URL)


@when("I check whether the triage is available")
def when_check(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(f"{OFFERS_URL}/triager")


@when(parsers.parse('I discard the offer of "{company}" because "{reason}"'))
def when_discard(client: TestClient, state: ScenarioState, company: str, reason: str) -> None:
    state.response = client.post(f"{_offer_url(client, company)}/discard", json={"reason": reason})


@when("I triage the offers")
def when_triage(client: TestClient, state: ScenarioState) -> None:
    state.response = client.post(TRIAGES_URL)


@when(parsers.parse('I preview the profile "{name}" with the excluded_keywords "{word}"'))
def when_preview(client: TestClient, state: ScenarioState, name: str, word: str) -> None:
    body = {"search_profile_id": _profile_id(client, name), "excluded_keywords": [word]}
    state.response = client.post(f"{OFFERS_URL}/criteria-previews", json=body)


# --- Then ---


@then(
    parsers.re(
        r"the triager discarded (?P<count>\d+) offers?"
        r'(?:: the offer of "(?P<company>[^"]+)")?$'
    )
)
def then_discarded(
    client: TestClient, state: ScenarioState, count: str, company: str | None
) -> None:
    batch = _ok(state.last_response)
    expected = [] if company is None else [_offer(client, company)["id"]]
    assert (batch["discarded"], batch["offer_ids"]) == (int(count), expected)


@then(parsers.re(r'the offer of "(?P<company>[^"]+)" is "(?P<status>[^"]+)"$'))
def then_status(client: TestClient, company: str, status: str) -> None:
    assert _offer(client, company)["status"] == status


@then(
    parsers.re(
        r'the offer of "(?P<company>[^"]+)" is "discarded" by the triager'
        r'(?: with reason "(?P<reason>[^"]+)" and (?:word "(?P<word>[^"]+)"|no word))?$'
    )
)
def then_discarded_by_triager(
    client: TestClient, company: str, reason: str | None, word: str | None
) -> None:
    offer = _offer(client, company)
    assert (offer["status"], offer["triager_discard"]) == ("discarded", "discarded")
    if reason is not None:
        assert (offer["discard_reason"], offer["discard_word"]) == (reason, word)


@then(parsers.parse('the offer of "{company}" is "discarded" by me'))
def then_discarded_by_me(client: TestClient, company: str) -> None:
    offer = _offer(client, company)
    assert offer["status"] == "discarded"
    assert offer["triager_discard"] != "discarded"


@then(parsers.parse('the offer of "{company}" is "pending", restored from a triager discard'))
def then_restored(client: TestClient, company: str) -> None:
    offer = _offer(client, company)
    assert (offer["status"], offer["triager_discard"]) == ("pending", "restored")


@then(parsers.parse("the triager would discard {count:d} offers"))
def then_discardable(state: ScenarioState, count: int) -> None:
    assert _ok(state.last_response, 200)["discardable"] == count


@then(parsers.parse('the offer triager was told the profile "{name}" and these decisions:'))
def then_told_decisions(state: ScenarioState, name: str, datatable: list[list[str]]) -> None:
    assert state.contexts, "the offer triager was not asked"
    context = state.contexts[-1]
    told = sorted(
        (d.title, str(d.status), str(d.reason or ""), d.word or "") for d in context.decisions
    )
    expected = sorted(
        (row["title"], row["decision"], row["reason"], row["word"]) for row in _rows(datatable)
    )
    assert ([terms.name for terms in context.profiles], told) == ([name], expected)


@then(
    parsers.re(
        r"the change would have filtered (?P<promoted>\d+) offers? I promoted "
        r"and (?P<discarded>\d+) I discarded"
    )
)
def then_preview(state: ScenarioState, promoted: str, discarded: str) -> None:
    preview = _ok(state.last_response, 200)
    counts = (preview["promoted_filtered"], preview["discarded_filtered"])
    assert counts == (int(promoted), int(discarded))
