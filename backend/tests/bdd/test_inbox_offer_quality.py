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
from funnel.modules.inbox.domain import OfferText, TriageAnswer, TriageContext
from funnel.modules.inbox.router import get_feed_client, get_offer_triager

pytestmark = pytest.mark.bdd

scenarios("inbox/offer_quality.feature")

OFFERS_URL = "/api/v1/offers"
LIST_FIELDS = frozenset({"titles", "keywords", "excluded_keywords"})
STAGES = ["evaluated", "applied", "screening", "interviewing", "offer", "accepted"]
# Past the 6 hours a job board waits between imports.
LATER = timedelta(hours=7)

Row = dict[str, str]


@dataclass
class ScenarioState:
    remoteok: list[Row] = field(default_factory=list)
    remoteok_id: str | None = None
    # What the fake offer triager answers, by company.
    answers: dict[str, TriageAnswer] = field(default_factory=dict)
    response: httpx2.Response | None = None

    @property
    def quality(self) -> dict[str, Any]:
        assert self.response is not None, "no request was made in this scenario"
        return _ok(self.response, 200)


@pytest.fixture
def state() -> ScenarioState:
    return ScenarioState()


class FakeOfferTriager:
    """Answers what the scenario says; an offer it knows nothing about has nothing to say."""

    def __init__(self, state: ScenarioState) -> None:
        self._state = state

    async def triage(
        self, offers: Sequence[OfferText], _context: TriageContext
    ) -> Mapping[int, TriageAnswer]:
        return {
            number: self._state.answers.get(offer.company, TriageAnswer())
            for number, offer in enumerate(offers)
        }


@pytest.fixture(autouse=True)
def fake_remoteok(client: TestClient, state: ScenarioState) -> Iterator[None]:
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
    overrides[get_offer_triager] = lambda: FakeOfferTriager(state)
    yield
    overrides.pop(get_feed_client, None)
    overrides.pop(get_offer_triager, None)
    overrides.pop(get_clock, None)


def _ok(response: httpx2.Response, status: int = 201) -> dict[str, Any]:
    assert response.status_code == status, response.text
    body: dict[str, Any] = response.json() if response.content else {}
    return body


def _offer(client: TestClient, company: str) -> dict[str, Any]:
    items = _ok(client.get(OFFERS_URL, params={"limit": "100"}), 200)["items"]
    offer: dict[str, Any] = next(o for o in items if o["company"] == company)
    return offer


def _offer_url(client: TestClient, company: str) -> str:
    return f"{OFFERS_URL}/{_offer(client, company)['id']}"


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
    header, *rows = datatable
    state.remoteok = [dict(zip(header, values, strict=True)) for values in rows]
    _ok(client.post(f"/api/v1/job-boards/{state.remoteok_id}/imports"))


@given(
    parsers.parse('the job board "Remote OK" was imported again without the offer of "{company}"')
)
def given_imported_again(client: TestClient, state: ScenarioState, company: str) -> None:
    state.remoteok = [row for row in state.remoteok if row["company"] != company]
    clock = FixedClock(datetime.now(UTC) + LATER)
    cast(FastAPI, client.app).dependency_overrides[get_clock] = lambda: clock
    _ok(client.post(f"/api/v1/job-boards/{state.remoteok_id}/imports"))
    cast(FastAPI, client.app).dependency_overrides.pop(get_clock)


@given(parsers.parse('an offer for "{company}" as "{title}"'))
def given_offer(client: TestClient, company: str, title: str) -> None:
    body = {"url": "https://jobs.example/hand", "company": company, "title": title}
    _ok(client.post(OFFERS_URL, json=body))


@given(parsers.parse('I promoted the offer of "{company}"'))
def given_promoted(client: TestClient, company: str) -> None:
    _ok(client.post(f"{_offer_url(client, company)}/promotion", json={}))


@given(parsers.parse('I discarded the offer of "{company}" because "{reason}"'))
def given_discarded(client: TestClient, company: str, reason: str) -> None:
    _ok(client.post(f"{_offer_url(client, company)}/discard", json={"reason": reason}))


@given(parsers.parse('I marked the offer of "{company}" as rightly filtered'))
def given_marked(client: TestClient, company: str) -> None:
    _ok(client.post(f"{_offer_url(client, company)}/rightly-filtered"))


@given(parsers.parse('the application for "{company}" moved to "{stage}"'))
def given_moved(client: TestClient, company: str, stage: str) -> None:
    application_id = _offer(client, company)["application_id"]
    current = _ok(client.get(f"/api/v1/applications/{application_id}"), 200)["stage"]
    # One stage at a time, as the funnel allows.
    for to_stage in STAGES[STAGES.index(current) + 1 : STAGES.index(stage) + 1]:
        url = f"/api/v1/applications/{application_id}/transitions"
        _ok(client.post(url, json={"to_stage": to_stage}))


@given(
    parsers.parse(
        'the offer triager answers for the offer of "{company}" with the reason "{reason}" '
        'and the evidence "{evidence}"'
    )
)
def given_answer(state: ScenarioState, company: str, reason: str, evidence: str) -> None:
    state.answers[company] = TriageAnswer(reason=reason, evidence=evidence)


@given("I triaged the offers")
def given_triaged(client: TestClient) -> None:
    _ok(client.post(f"{OFFERS_URL}/triages"))


# --- When ---


@when("I view the offer quality")
def when_view(client: TestClient, state: ScenarioState) -> None:
    state.response = client.get(f"{OFFERS_URL}/quality")


# --- Then ---


@then(parsers.re(r"the precision is (?P<precision>[\d.]+)% of (?P<decided>\d+) decided offers?"))
def then_precision(state: ScenarioState, precision: str, decided: str) -> None:
    total = state.quality["total"]
    assert (total["precision"], total["decided"]) == (float(precision), int(decided))


@then("there is no precision")
def then_no_precision(state: ScenarioState) -> None:
    total = state.quality["total"]
    assert (total["precision"], total["decided"]) == (None, 0)


@then(
    parsers.re(
        r"the losses are (?P<losses>[\d.]+)% of (?P<reviewed>\d+) reviewed near miss(es)?, "
        r"with (?P<left>\d+) left to review"
    )
)
def then_losses(state: ScenarioState, losses: str, reviewed: str, left: str) -> None:
    quality = state.quality
    found = (
        quality["total"]["losses"],
        quality["total"]["reviewed_near_misses"],
        quality["near_misses_left"],
    )
    assert found == (float(losses), int(reviewed), int(left))


@then(parsers.re(r"there are no losses, with (?P<left>\d+) near miss(es)? left to review"))
def then_no_losses(state: ScenarioState, left: str) -> None:
    quality = state.quality
    assert (quality["total"]["losses"], quality["near_misses_left"]) == (None, int(left))


@then(parsers.parse("{fitting:d} offers fit this week and {average:f} a week on average"))
def then_flow(state: ScenarioState, fitting: int, average: float) -> None:
    quality = state.quality
    found = (quality["weeks"][-1]["fitting"], quality["total"]["fitting"])
    assert (found, quality["fitting_per_week"]) == ((fitting, fitting), average)


@then(
    parsers.parse(
        "of {promoted:d} promoted offers, {applied:d} reached applied "
        "and {answered:d} got an answer"
    )
)
def then_real_result(state: ScenarioState, promoted: int, applied: int, answered: int) -> None:
    total = state.quality["total"]
    assert (total["promoted"], total["applied"], total["answered"]) == (promoted, applied, answered)


@then("the discards by reason are:")
def then_discards(state: ScenarioState, datatable: list[list[str]]) -> None:
    _, *rows = datatable
    expected = [{"reason": reason, "offers": int(offers)} for reason, offers in rows]
    assert state.quality["discard_reasons"] == expected


@then("the sources are:")
def then_sources(state: ScenarioState, datatable: list[list[str]]) -> None:
    header, *rows = datatable
    expected = [
        {
            key: value if key == "source" else int(value)
            for key, value in zip(header, row, strict=True)
        }
        for row in rows
    ]
    assert state.quality["sources"] == expected


@then(
    parsers.re(
        r"the triager's precision is (?P<precision>[\d.]+)% of (?P<decided>\d+) suggested "
        r"discards decided"
    )
)
def then_triager_precision(state: ScenarioState, precision: str, decided: str) -> None:
    total = state.quality["total"]
    found = (total["triager_precision"], total["suggested_decided"])
    assert found == (float(precision), int(decided))


@then(
    parsers.re(
        r"the triager's misses are (?P<misses>[\d.]+)% of (?P<discarded>\d+) triaged offers "
        r"discarded"
    )
)
def then_triager_misses(state: ScenarioState, misses: str, discarded: str) -> None:
    total = state.quality["total"]
    found = (total["triager_misses"], total["triaged_discarded"])
    assert found == (float(misses), int(discarded))


@then("there is no triager precision and there are no triager misses")
def then_no_triager_figures(state: ScenarioState) -> None:
    total = state.quality["total"]
    assert (total["triager_precision"], total["triager_misses"]) == (None, None)
